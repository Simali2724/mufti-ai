"""Per-claim verification against the complete supporting source span.

Claims are judged one by one and independently: an unsupported claim is removed while the
other supported claims survive, instead of the whole answer being accepted or thrown away.
A quote match alone never counts as proof — the span must actually entail the claim, keep its
subject and keep the attribution of whoever is being quoted.
"""
import json
import re
from app.core import diagnostics
from app.core.config import settings
from app.core.language import detect
from app.llm.prompts import VERIFY_RULES
from app.llm.router import get_chat_model

# Rejection codes whose evidence is sound and whose sentence can be rewritten from the same
# span. `repair_agent` routes on these; everything else is abandoned, because there is
# nothing in its evidence to repair.
REPAIRABLE_CODES = frozenset({'attribution', 'incomplete', 'language', 'not_entailed',
                              'off_question', 'empty', 'hedge_dropped', 'copied_span',
                              'weak_grounding', 'multi_sentence'})

CONNECTORS = {'and', 'or', 'because', 'the', 'to', 'of', 'in', 'that', 'with', 'for',
              'اور', 'یا', 'کے', 'کی', 'کا', 'کو', 'سے', 'نے', 'میں', 'کہ',
              'और', 'या', 'के', 'की', 'को', 'से', 'में', 'कि'}


def canonical(text):
    out, positions = [], []
    for index, char in enumerate(text):
        if char in '‎‏‪‫‬‭‮⁦⁧⁨⁩':
            continue
        char = ' ' if char.isspace() else char
        if char == ' ' and (not out or out[-1] == ' '):
            continue
        out.append(char)
        positions.append(index)
    return ''.join(out).strip(), positions


def locate_offsets(source, quote):
    """(start, end) of `quote` inside `source`, ignoring whitespace and direction marks."""
    clean, positions = canonical(source)
    needle, _ = canonical(quote)
    start = clean.find(needle)
    if not needle or start < 0:
        return None
    return positions[start], positions[start + len(needle) - 1] + 1


def locate_quote(source, quote):
    """Exact location of `quote` inside `source`, ignoring whitespace and direction marks."""
    found = locate_offsets(source, quote)
    return None if found is None else source[found[0]:found[1]]


TERMINATORS = ('.', '!', '?', '۔', '؟', '।')

# "Surname, Title , p. 155." — how this book cites an outside writer it is quoting.
OUTSIDE_CITATION = re.compile(
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z.]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z.]+)*)*)\s*,\s*'
    r'[A-Z][^,]{6,80},\s*p\.?\s*\d*')
NAME_STOPWORDS = {'The', 'A', 'An', 'This', 'That', 'In', 'On', 'Of', 'For', 'And', 'Or', 'But',
                  'It', 'They', 'He', 'She', 'We', 'You', 'I', 'His', 'Her', 'Their', 'Its'}


def quoted_authorities(text):
    """Surnames of outside writers the passage itself credits, e.g. Inglehart and Norris.

    The brief is explicit that a view the book quotes from a named researcher is not
    automatically the book's own conclusion, so a claim resting on such a span has to say
    whose statement it is.
    """
    names = set()
    for match in OUTSIDE_CITATION.finditer(text):
        for part in match.group(1).split(','):
            for word in part.split():
                word = word.strip('.')
                if len(word) > 2 and word[0].isupper() and word not in NAME_STOPWORDS:
                    names.add(word)
    return names


def attribution_cutoff(text):
    """Offset at which the last outside-writer citation in this passage ends, or -1.

    This book prints the citation AFTER the material it is crediting ("… p. 155."), so the
    last citation closes the quoted region. Text that resumes after it is the book speaking
    again in its own voice.
    """
    ends = [match.end() for match in OUTSIDE_CITATION.finditer(text)]
    return max(ends) if ends else -1


def needs_attribution(window_text, support):
    """Does a claim resting on THIS span have to name the writer the passage quotes?

    The brief is explicit that attribution must attach to the actual quoted span, not to
    every sentence in a passage that happens to carry a footnote somewhere. So the test is
    positional: a span that lies inside the region a citation closes is quoted material and
    its claim must say whose statement it is; a span that comes after the last citation is
    the book's own prose and is not forced to credit an unrelated writer.
    """
    cutoff = attribution_cutoff(window_text)
    if cutoff < 0:
        return False
    found = locate_offsets(window_text, support)
    if found is None:
        return True
    return found[0] < cutoff


PROSE_AFTER_CITATION = re.compile(r'[A-Za-z؀-ۿऀ-ॿ]{2,}')

# Words with which the book marks a statement as tentative rather than asserted.
HEDGES = re.compile(
    r'(?<!\w)(could|may|might|perhaps|possibly|plausibly|probably|likely|seems?|appears?|'
    r'suggests?|arguably|apparently|allegedly|reportedly|'
    r'shayad|mumkin|ho sakta|lagta|غالبا|شاید|ممکن|سکتا|سکتی|گویا|'
    r'शायद|संभव|सकता|सकती|लगता)(?!\w)', re.I)
SENTENCES = re.compile(r'(?<=[۔؟।.!?])\s+')


def best_sentence(support, claim_text):
    """The sentence of the span the claim actually restates, by word overlap."""
    parts = [part for part in SENTENCES.split(support) if part.strip()]
    if len(parts) < 2:
        return support
    from app.ingestion.normalize import tokens as normalise
    wanted = set(normalise(claim_text))
    return max(parts, key=lambda part: len(wanted & set(normalise(part))))


MIN_PARAPHRASE_TOKENS = 8
COPY_RUN_RATIO = .6
# The answer and repair prompts have always asked for ONE sentence of at most 30 words per
# claim. Enforcing it in code closes a real escape route, measured on this book: asked to
# repair a fabricated claim, the local model kept the fabrication and GLUED a correct,
# properly attributed sentence onto the end of it. Each guard then passed on its own — names
# present, hedge present, wording shared with the span — while the claim as a whole still
# asserted something the book never says. A claim that makes two statements cannot be
# verified as one, so it is sent back as one more thing to repair.
MAX_CLAIM_WORDS = 45


def sentence_count(text):
    stripped = str(text or '').strip().rstrip('"”’)]}').rstrip()
    stripped = re.sub(r'[.?!۔؟।]+$', '', stripped)
    return len([part for part in SENTENCES.split(stripped) if part.strip()])
# A same-script claim must reuse at least this share of its own content words from its span,
# AND must not invent more than MIN_INVENTED_TOKENS content words the span never uses. Both
# conditions are needed: the ratio alone refuses short loose paraphrases that the model
# verifier is perfectly able to judge, while the absolute count is what actually separates a
# fabricated position from a compressed restatement. Measured on the cases in
# tests/test_answer_quality.py the approved fabrication invents 10 words against a ratio of
# .23, and the loosest paraphrase the suite accepts invents 5.
SUPPORT_FLOOR = .4
MIN_GROUNDING_TOKENS = 5
MIN_INVENTED_TOKENS = 8


def content_tokens(text, ignore=()):
    from app.ingestion.normalize import tokens as normalise
    from app.retrieval.query_expansion import ALL_QUESTION_WORDS
    skip = {str(word).lower() for word in ignore}
    return [t for t in normalise(text)
            if len(t) > 1 and t not in ALL_QUESTION_WORDS and t.lower() not in skip]


def same_script(left, right):
    return detect(left) == detect(right)


def weakly_grounded(claim_text, support, passage=''):
    """True when a same-language claim shares too little wording with the span it cites.

    Keyword overlap is NOT sufficient for support — the model verifier still has to judge
    entailment — but for a claim written in the span's own language it is necessary. Measured
    fabrication this catches, which a 1.7B verifier approved: from a span saying the cultural
    fault line between the west and Islam "involves issues of gender equality", the drafter
    produced "Gender equality is a fundamental principle in Islam, emphasizing the equal
    rights and responsibilities of men and women in all aspects of life." Nothing about
    rights, responsibilities or Islamic principle appears in that span; the sentence shares
    three content words with it and invents the rest.

    It is deliberately NOT applied across scripts. A faithful English explanation of an Urdu
    passage shares no tokens with it by construction, and refusing those would break the
    multilingual answering this application exists for; there the model verdict stands alone.
    """
    if not same_script(claim_text, support):
        return False
    # The attribution guard REQUIRES the writers' names in the claim, and they are printed in
    # the citation line rather than inside the quoted span, so counting them as unsupported
    # wording would penalise a claim for obeying another rule.
    names = quoted_authorities(passage or support)
    claim_words = content_tokens(claim_text, names)
    if len(claim_words) < MIN_GROUNDING_TOKENS:
        return False
    span_words = set(content_tokens(support, names))
    shared = sum(word in span_words for word in claim_words)
    invented = len(claim_words) - shared
    return shared / len(claim_words) < SUPPORT_FLOOR and invented >= MIN_INVENTED_TOKENS


def longest_shared_run(claim_tokens, span_tokens):
    """Longest run of consecutive tokens the claim shares with the span."""
    best, previous = 0, {}
    for index, token in enumerate(claim_tokens):
        current = {}
        for position, other in enumerate(span_tokens):
            if token == other:
                current[position] = previous.get(position - 1, 0) + 1
                best = max(best, current[position])
        previous = current
    return best


def copies_span(claim_text, support):
    """True when the claim is the span pasted back rather than explained.

    The reader asked for an explanation in the assistant's own words, not quotations, and
    the answer prompt has always said so. Once the qualification guard above started
    rejecting flattened paraphrases, the cheapest way for a small model to satisfy it was to
    reproduce the sentence verbatim — which satisfied every other check and still gave the
    reader a pasted quote. The source text is already shown to the reader under Sources, so a
    claim that is mostly one contiguous run of the span carries nothing new. Short claims are
    exempt: there is no way to restate a seven-word statement without reusing its words.
    """
    from app.ingestion.normalize import tokens as normalise
    claim_tokens, span_tokens = normalise(claim_text), normalise(support)
    if len(claim_tokens) < MIN_PARAPHRASE_TOKENS or not span_tokens:
        return False
    run = longest_shared_run(claim_tokens, span_tokens)
    return run >= MIN_PARAPHRASE_TOKENS and run / len(claim_tokens) >= COPY_RUN_RATIO


def drops_qualification(claim_text, support):
    """True when the sentence being restated hedges and the claim asserts it flatly.

    The brief requires the book's qualifications to survive into the answer. Measured case:
    page 50's span says gender equality "could plausibly lie at the heart of any clash"; the
    local model restated that as a flat "are central to", which reads as the book asserting
    something it carefully did not. The check is scoped to the ONE sentence of the span that
    the claim restates, so an unrelated hedge elsewhere in a long passage does not reject a
    claim that never touched it.
    """
    sentence = best_sentence(support, claim_text)
    return bool(HEDGES.search(sentence)) and not HEDGES.search(claim_text)


def is_only_reference(support):
    """A bare bibliographic line supports no statement, however well it matches the question."""
    stripped = OUTSIDE_CITATION.sub(' ', support)
    stripped = re.sub(r'[\d\s.,;:()\[\]\-–—«»“”"\'/]+', ' ', stripped)
    return len(PROSE_AFTER_CITATION.findall(stripped)) < 3


# Question words that demand a SPECIFIC relation in the answer: a reason, a time, an agent.
RELATION_WORDS = re.compile(
    r'(?<!\w)(why|how|when|where|who|whom|whose|which|'
    r'kyun|kyon|kaise|kab|kahan|kaun|kitne|kitni|'
    r'کیوں|کیسے|کب|کہاں|کون|کتنے|'
    r'क्यों|कैसे|कब|कहाँ|कहां|कौन|कितने)(?!\w)', re.I)


def demands_relation(question):
    """Does the question ask for a particular relation, or just for a topic to be explained?

    This decides whether the verifier's `answers_question` verdict is a hard gate.

    Measured failure that forced the distinction: on "Explain Gender Equality in detail" the
    local 1.7B verifier returned answers_question=false for two claims while its own feedback
    for those same claims read "The claim is fully entailed by the span." A relevance verdict
    that contradicts itself must not be the reason a correctly attributed, concept-correct,
    entailed claim is discarded — that is a false refusal manufactured by the verifier.

    For a broad topical request any supported on-concept claim about the topic does answer it,
    and the concept guard above has already proved the claim is on that topic. Where the
    question genuinely demands a reason, a date or an agent, the verdict still gates, because
    there it carries real information: "Many books follow this book" does not answer "Why
    study biography?", and that case is still rejected.
    """
    return bool(RELATION_WORDS.search(question or ''))


def quoted_attributions(text):
    """Full names of the outside writers, in the order the passage credits them.

    `quoted_authorities` answers "is attribution required"; this answers "whose name does a
    repaired claim have to carry", which is what a targeted repair needs to write.
    """
    names, seen = [], set()
    for match in OUTSIDE_CITATION.finditer(text):
        for part in match.group(1).split(','):
            words = [word.strip('.') for word in part.split()]
            name = ' '.join(word for word in words
                            if len(word) > 1 and word[0].isupper() and word not in NAME_STOPWORDS)
            if name and name.lower() not in seen:
                seen.add(name.lower())
                names.append(name)
    return names


def concept_forms(concept_ids):
    """Every reviewed surface form, in any script, of the concepts the question matched."""
    from app.retrieval.query_expansion import load_lexicon
    wanted = set(concept_ids or ())
    if not wanted:
        return []
    return [form for entry in load_lexicon() if entry.get('id') in wanted
            for group in entry.get('forms', {}).values() for form in group]


def competing_forms(concept_ids):
    """(id, forms) for every reviewed concept the question did NOT ask about."""
    from app.retrieval.query_expansion import load_lexicon
    wanted = set(concept_ids or ())
    if not wanted:
        return []
    return [(entry['id'], [form for group in entry.get('forms', {}).values() for form in group])
            for entry in load_lexicon() if entry.get('id') not in wanted]


def concept_guard(concept_ids):
    """The asked-about forms plus the rival concepts a span could be confused with."""
    asked = concept_forms(concept_ids)
    if not asked:
        return {}
    return {'asked': asked, 'competing': competing_forms(concept_ids)}


def _as_guard(value):
    """Accept either the guard dict or a plain list of asked forms (older callers/tests)."""
    if isinstance(value, dict):
        return value
    forms = list(value or ())
    return {'asked': forms, 'competing': []} if forms else {}


def mentions_concept(text, forms):
    """True when the text carries one of the reviewed surface forms of the question's concept."""
    from app.ingestion.normalize import tokens as normalise
    present = set(normalise(text))
    for form in forms:
        parts = normalise(form)
        if parts and all(part in present for part in parts):
            return True
    return False


def terminate(text, language):
    """Add the script's full stop when a claim is otherwise complete but unpunctuated.

    Punctuation is presentation, not evidence. Dropping a claim whose span fully supports it
    because the model omitted a final full stop is a false refusal, so the sentence is closed
    here instead. A claim that trails off in a connector is still rejected below: that is an
    incomplete statement, not a missing character.
    """
    stripped = text.rstrip()
    if not stripped or stripped.rstrip('"”’)]}').rstrip().endswith(TERMINATORS):
        return text
    return stripped + ('۔' if language == 'Urdu' else '।' if language == 'Hindi' else '.')


def diagnose(claim, window, language, guard=()):
    """(code, message) for the first code-checkable rule this claim breaks, or ('', '').

    The code is what the targeted repair node routes on: a claim that merely dropped an
    attribution or trailed off mid-sentence can be redrafted from the very same span, while
    a claim resting on the wrong concept's span has nothing to repair.
    """
    guard = _as_guard(guard)
    text = claim.get('text', '')
    if not isinstance(text, str) or not text.strip():
        return 'empty', 'Empty claim'
    if re.search(r'https?://|<|>', text):
        return 'markup', 'Unexpected markup'
    support = claim.get('support', '')
    if not support or len(support.split()) < 3:
        return 'no_span', 'No supporting span was cited'
    if locate_quote(window['text'], support) is None:
        return 'span_absent', 'Cited span is not present verbatim on that page'
    # A bibliographic line locates a source; it states nothing that a claim can rest on.
    if is_only_reference(support):
        return 'reference_only', 'Cited span is only a bibliographic reference, not a statement'
    ending = text.rstrip().rstrip('"”’)]}').rstrip()
    words = re.sub(r'[.?!۔؟।]+$', '', ending).split()
    if not words or words[-1].lower() in CONNECTORS:
        return 'incomplete', 'Incomplete sentence ending in a connector'
    if language in ('Hindi', 'Urdu') and detect(text) != language:
        return 'language', 'Wrong reply script'
    if language in ('English', 'Hinglish') and detect(text) in ('Hindi', 'Urdu'):
        return 'language', 'Wrong reply script'
    # The question named a reviewed concept, so a claim must not rest on an ADJACENT concept's
    # span. Measured failure this catches: a gender-equality question drew three approved
    # claims from a page whose span reads "آئینی مساوات" — CONSTITUTIONAL equality between the
    # Charter's parties, a separate lexicon concept — and the local verifier accepted
    # statements about the Quran and about "both genders" that the span never makes. Such a
    # passage is still shown, as related material, never as support.
    #
    # Requiring the concept WORD in the span itself was too strong, and the brief says so:
    # a faithful paraphrase of the next sentence of the same quoted paragraph does not have
    # to repeat the keyword. So the rule is now scoped three ways: the span carries the asked
    # concept (accept), the span carries a rival reviewed concept instead (reject, by name),
    # or the span carries neither and is only accepted when its own parent paragraph is about
    # the asked concept.
    if guard and not mentions_concept(support, guard['asked']):
        rival = next((cid for cid, forms in guard['competing'] if mentions_concept(support, forms)), '')
        if rival:
            return 'wrong_concept', ('Cited span carries a different concept ('
                                     + rival.replace('_', ' ') + ') than the question asked about')
        if not mentions_concept(window['text'], guard['asked']):
            return 'wrong_concept', 'Cited span carries a different concept than the question asked about'
    if sentence_count(text) > 1 or len(text.split()) > MAX_CLAIM_WORDS:
        return 'multi_sentence', ('A claim must be ONE sentence. State the single point this '
                                  'span supports and nothing else')
    if weakly_grounded(text, support, window['text']):
        return 'weak_grounding', ('The claim is written in the span\'s own language but shares '
                                  'almost none of its wording; state only what the span says')
    if copies_span(text, support):
        return 'copied_span', ('The claim reproduces the source sentence instead of explaining '
                               'it. Say the same thing in your own words')
    if drops_qualification(text, support):
        return 'hedge_dropped', ('The source hedges this statement; the claim asserts it as '
                                 'settled fact. Keep the qualification the book used')
    # A view the book quotes from a named outside writer must not become the book's own —
    # but only where the span actually sits inside the region that citation closes.
    authorities = quoted_authorities(window['text'])
    if authorities and needs_attribution(window['text'], support) \
            and not any(name.lower() in text.lower() for name in authorities):
        return 'attribution', ('Quoted outside view stated without its attribution to '
                               + ', '.join(sorted(authorities)))
    return '', ''


def structural_problem(claim, window, language, guard=()):
    """Message for the first code-checkable rule this claim breaks, or ''."""
    return diagnose(claim, window, language, guard)[1]


def structural_pass(draft, windows, language, guard=()):
    """Drop claims that fail a code-checkable rule before spending a model call."""
    by_id = {w['source_id']: w for w in windows}
    kept, rejected = [], []
    for claim in draft.get('claims', []):
        window = by_id.get(claim.get('source_id'))
        if window is None:
            rejected.append({**claim, 'reason': 'Unknown source', 'code': 'unknown_source'})
            continue
        claim['text'] = terminate(str(claim.get('text', '')), language)
        code, problem = diagnose(claim, window, language, guard)
        if problem:
            rejected.append({**claim, 'reason': problem, 'code': code})
        else:
            kept.append(claim)
    return kept, rejected


async def verify_batch(question, language, claims):
    """One model call over at most `answer_max_claims` claims, each with its own span.

    Claim ids are renumbered 1..n inside the batch so they always fit the verifier schema's
    id range, then mapped back. Without this, a long sectioned answer drafted more claims
    than the schema could reference and every claim past the limit was discarded for
    "no verdict returned" even though its span supported it.
    """
    local_to_claim = {index + 1: claim['claim_id'] for index, claim in enumerate(claims)}
    payload = {'question': question, 'reply_language': language,
               'claims': [{'claim_id': index + 1, 'claim': claim['text'],
                           'source_pdf_page': claim['page'], 'source_span': claim['support']}
                          for index, claim in enumerate(claims)]}
    report, provider = await get_chat_model('verifier').invoke(VERIFY_RULES,
                                                              json.dumps(payload, ensure_ascii=False), True)
    verdicts = {}
    rows = report.get('claims') if isinstance(report, dict) else None
    for index, row in enumerate(rows or []):
        if not isinstance(row, dict):
            continue
        local_id = row.get('claim_id')
        if not isinstance(local_id, int) or local_id not in local_to_claim:
            local_id = index + 1 if index + 1 in local_to_claim else None
        if local_id is None:
            continue
        verdicts[local_to_claim[local_id]] = {
            'supported': row.get('supported') is True,
            'attribution_correct': row.get('attribution_correct') is not False,
            'answers_question': row.get('answers_question') is True,
            'feedback': str(row.get('feedback', ''))[:300],
        }
    language_correct = report.get('language_correct') is not False if isinstance(report, dict) else True
    return verdicts, language_correct, provider


async def model_pass(question, language, claims):
    """Verify every claim, in batches that fit the verifier schema's claim id range."""
    size = max(1, settings.answer_max_claims)
    verdicts, language_correct, provider = {}, True, ''
    for start in range(0, len(claims), size):
        batch = claims[start:start + size]
        batch_verdicts, batch_language, provider = await verify_batch(question, language, batch)
        verdicts.update(batch_verdicts)
        language_correct = language_correct and batch_language
    return verdicts, language_correct, provider


def prune(draft, keep_ids):
    for section in draft.get('sections', []):
        section['claims'] = [c for c in section['claims'] if c['claim_id'] in keep_ids]
    draft['sections'] = [s for s in draft['sections'] if s['claims']]
    draft['claims'] = [c for c in draft['claims'] if c['claim_id'] in keep_ids]
    return draft


async def run(state):
    draft = state.get('draft_answer', {}) or {}
    windows = state.get('evidence_windows') or []
    language = state['detected_language']
    claims = draft.get('claims', [])
    if not claims:
        diagnostics.record('verification', verified=0, rejected=0, note='no claims drafted')
        return {'verification_report': {'passed': False, 'verified_claims': 0, 'rejected': [],
                                        'feedback': 'No directly supported claim was drafted.'},
                'draft_answer': {**draft, 'coverage': 'none'},
                'retries': state.get('retries', 0) + 1}
    kept, rejected = structural_pass(draft, windows, language,
                                     concept_guard(state.get('matched_concepts')))
    # A claim that already passed verification in an earlier round is not re-judged. The
    # repair node puts the surviving claims back into the draft alongside the rewritten ones,
    # and re-verifying them would cost another local model call to reach the same verdict —
    # and risk a small model contradicting itself and discarding work that was already sound.
    settled = [claim for claim in kept if claim.get('verified')]
    kept = [claim for claim in kept if not claim.get('verified')]
    verdicts, language_correct, provider = {}, True, ''
    if kept:
        try:
            verdicts, language_correct, provider = await model_pass(state['user_input'], language, kept)
        except Exception as exc:
            diagnostics.record('verification', failure=type(exc).__name__)
            return {'verification_report': {'passed': False, 'verified_claims': 0, 'rejected': [],
                                            'service_failure': True,
                                            'feedback': 'Verifier unavailable; answer withheld'},
                    'errors': state.get('errors', []) + ['Verifier unavailable: ' + type(exc).__name__],
                    'retries': state.get('retries', 0) + 1}
    relation_required = demands_relation(state['user_input'])
    verified, advisory = list(settled), []
    for claim in kept:
        verdict = verdicts.get(claim['claim_id'])
        # The relevance verdict is a hard gate only where the question demands a relation.
        relevance_ok = verdict is not None and (verdict['answers_question'] or not relation_required)
        if verdict is None:
            rejected.append({**claim, 'reason': 'No verdict returned for this claim', 'code': 'no_verdict'})
        elif not (verdict['supported'] and verdict['attribution_correct'] and relevance_ok):
            code, reason = (('not_entailed', 'Not entailed by its span') if not verdict['supported']
                            else ('attribution', 'Attribution or subject changed')
                            if not verdict['attribution_correct']
                            else ('off_question', 'Does not answer the question'))
            rejected.append({**claim, 'code': code,
                             'reason': f"{reason}: {verdict['feedback']}".strip(': ')})
        else:
            claim['verified'] = True
            if not verdict['answers_question']:
                # Kept, but recorded: the claim is entailed and on-concept, and the question
                # asked for the topic rather than for a specific relation. Coverage drops to
                # partial so the reader is never told this is the whole answer.
                claim['relevance_verdict'] = 'advisory'
                advisory.append(claim['claim_id'])
            verified.append(claim)
    if not language_correct:
        rejected += [{**c, 'reason': 'Wrong reply language', 'code': 'language'} for c in verified]
        verified = []
    draft = prune(draft, {c['claim_id'] for c in verified})
    if verified:
        has_missing = bool(draft.get('missing_aspects')) or bool(rejected) or bool(advisory)
        draft['coverage'] = 'partial' if (draft.get('coverage') == 'partial' or has_missing) else 'full'
    else:
        draft['coverage'] = 'none'
    report = {
        'passed': bool(verified),
        'verified_claims': len(verified),
        'rejected': [{'claim_id': r.get('claim_id'), 'text': r.get('text', '')[:200],
                      'page': r.get('page'), 'reason': r['reason'], 'code': r.get('code', '')}
                     for r in rejected],
        # The whole claim, span and all, so the repair node can rewrite that one sentence
        # from its own evidence instead of the pipeline redrafting the entire answer.
        'rejected_claims': rejected,
        'verifier_provider': provider,
        'feedback': '; '.join(dict.fromkeys(r['reason'] for r in rejected))[:400],
    }
    diagnostics.record('verification', verified=len(verified), rejected=len(rejected),
                       rejections=[r['reason'] for r in rejected][:8], coverage=draft['coverage'],
                       carried_over=len(settled), relation_question=relation_required,
                       kept_on_advisory_relevance=advisory,
                       repairable=sorted({r.get('code', '') for r in rejected} & REPAIRABLE_CODES))
    return {'verification_report': report, 'draft_answer': draft, 'retries': state.get('retries', 0) + 1}


# Preserved for the existing regression tests and any external caller.
def validate_claims(draft, chunks, language):
    windows = [{'source_id': i + 1, 'text': c['text'],
                'spans': [{'span_id': 1, 'text': c['text']}]} for i, c in enumerate(chunks)]
    claims = draft.get('claims', [])
    if not claims:
        return False, 'No directly supported answer'
    if len(claims) > settings.answer_max_claims:
        return False, 'Too many claims'
    for claim in claims:
        if not isinstance(claim, dict):
            return False, 'Invalid claim'
        source_id = claim.get('source_id')
        if not isinstance(source_id, int) or not 1 <= source_id <= len(windows):
            return False, 'Invalid source ID'
        quote = claim.get('support') or claim.get('quote', '')
        if not isinstance(quote, str) or len(quote.strip()) < 12:
            return False, 'Quote must be 12+ characters'
        matched = locate_quote(windows[source_id - 1]['text'], quote)
        if matched is None:
            return False, 'Quote does not exist verbatim on cited page'
        claim['support'] = matched
        problem = structural_problem({**claim, 'support': matched}, windows[source_id - 1], language)
        if problem:
            return False, problem
    return True, ''
