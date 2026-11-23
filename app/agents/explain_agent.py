"""Explanation answer path: one streamed, teacher-style, cited answer, then a faithfulness audit.

Why this exists (2026-11-16). The reader's requirement is explicit: any question about the book
must get a complete, respectful, well-explained answer the way a good chat assistant explains,
and the app must not refuse when the book does carry the answer. The claim pipeline
(answer_agent -> verifier_agent -> repair_agent) writes at most eight one-sentence claims of 30
words and discards every claim a verifier rejects; on real use that produced terse lists and
frequent refusals of answerable questions.

This path keeps grounding with different, measurable mechanics:
  1. The model sees only book passages (readable spans of the selected evidence windows).
  2. Every factual sentence must carry a [n] citation; citations are validated in code against
     the sources actually supplied and renumbered for display.
  3. A separate audit call checks every sentence against ALL sources and returns only the
     problem sentences with a minimal fix (or "" to delete). Fixes are applied in code. A bad
     sentence is corrected or removed; the rest of a correct answer is kept.
  4. If the model finds nothing relevant it answers <<none>>, and the formatter shows the
     related pages honestly, exactly as before.

`settings.answer_mode = "strict"` restores the claim pipeline unchanged.
"""
import asyncio
import json
import re
import time
import unicodedata
from app.core import diagnostics
from app.core.config import settings
from app.core.logging import logger
from app.llm.prompts import EXPLAIN_RULES, AUDIT_RULES
from app.llm.router import get_chat_model
from app.llm.progress import draft_reset
from app.retrieval.evidence import readable_spans, legible_pieces, display_quote
from app.agents import suggest

MARKER = re.compile(r'<<\s*(full|partial|none)\s*(?::\s*([\d,\s،]*))?>>', re.I)
# [2], [1, 3], [1،3], [Source 2], [S2]
CITE = re.compile(r'\[\s*(?:sources?\s*|S)?(\d{1,2}(?:\s*[,،]\s*(?:sources?\s*|S)?\d{1,2})*)\s*\]', re.I)
SENTENCE = re.compile(r'[^.!?۔।؟\n]+(?:[.!?۔।؟]+(?:\s*\[[^\]\n]{1,20}\])*|$)')
WORD = re.compile(r'\w+', re.U)
ABBREVIATION = re.compile(r'\b(?:[A-Z]|Dr|Mr|Mrs|Ms|St|Prof|Sr|Jr|Vol|No|pp?|vs|cf|e\.g|i\.e|ca)\.(?=\s)')


# ------------------------------------------------------------------ sources
def build_sources(windows):
    """Number the readable windows 1..n. Unreadable OCR is never shown to the model as text."""
    sources = []
    for window in windows:
        text = ' '.join(legible_pieces(window.get('text', ''))).strip()
        if text:
            sources.append({'n': len(sources) + 1, 'window': window, 'text': text})
    return sources


def sources_block(sources):
    from app.agents.verifier_agent import quoted_authorities
    blocks = []
    for source in sources:
        window = source['window']
        head = f"[{source['n']}] {book_display_title(window.get('book_id', ''), window.get('book_title', ''))} — PDF page {window['page_start']}"
        if window.get('chapter'):
            head += f" — section: {window['chapter']}"
        notes = []
        writers = quoted_writers(window.get('text', ''))
        if writers:
            notes.append('contains quotations credited in its footnotes to ' + '; '.join(writers)
                         + ' — present those statements as their words, not as the book’s own conclusion')
        if window.get('relation') not in (None, 'same_concept'):
            notes.append('adjacent topic — use only for what it actually says')
        if notes:
            head += ' (' + '; '.join(notes) + ')'
        blocks.append(head + '\n' + source['text'])
    return '\n\n'.join(blocks)


def quoted_writers(text):
    """Full names of the outside writers a passage credits ("Ronald L. Nettler"), in order.

    The surname set from verifier_agent.quoted_authorities lists first names and surnames as
    separate words ("Cardinal, David, Marquand, Nettler, Ronald, Southern" on page 51), which
    measured 2026-11-16 left the model unable to tell the passage was a quotation at all.
    """
    from app.agents.verifier_agent import OUTSIDE_CITATION, NAME_STOPWORDS
    names = []
    for match in OUTSIDE_CITATION.finditer(text or ''):
        # "Ronald Inglehart and Pippa Norris, Title, p. 155": the pattern starts at the second
        # author, so pick up a co-author joined by "and"/"&" just before it.
        before = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z.]+)+)\s+(?:and|&)\s+$', (text or '')[:match.start()])
        if before and before.group(1) not in names:
            names.append(before.group(1))
        for part in match.group(1).split(','):
            name = ' '.join(w for w in part.split() if w not in NAME_STOPWORDS).strip(' .')
            if len(name) > 3 and name not in names:
                names.append(name)
    return names[:6]


def conversation_context(state):
    """The last two turns, so a follow-up such as "explain more" or "aur batao" makes sense."""
    turns = []
    for turn in (state.get('history') or [])[-2:]:
        answer = re.sub(r'\s+', ' ', MARKER.sub('', str(turn.get('answer', ''))))[:700]
        turns.append(f"Reader: {turn.get('question', '')}\nMufti AI: {answer}")
    return '\n\n'.join(turns)


# Answer styles chosen by the reader (ChatRequest.answer_style). A style changes length and
# layout only; it never relaxes GROUNDING, CITATIONS or ADAB, and the audit is identical.
# 'short' is also the fastest choice on the local 2 GB GPU: output tokens are the real cost.
STYLE_NOTES = {
    'detailed': '',
    'short': ('STYLE (the reader chose SHORT — this overrides the length guidance in FORMAT): '
              '80-180 words. A direct answer of one to three sentences, then at most four bullet '
              'points. No section headings and no summary section. Every factual sentence still '
              'carries its [n] citation.'),
    'simple': ('STYLE (the reader chose SIMPLE WORDS — this overrides the length guidance in FORMAT): '
               'explain as to a beginner or a young student, 200-450 words. Short sentences, everyday '
               'words, every Arabic or technical term explained in brackets the first time. Use at most '
               'three ### headings. Do not add examples, comparisons or facts the sources do not '
               'contain. Every factual sentence still carries its [n] citation.'),
    'points': ('STYLE (the reader chose STUDY NOTES — this overrides the layout guidance in FORMAT): '
               'a one-line answer, then organised bullet-point notes under ### headings, key terms in '
               '**bold**, 200-500 words, ending with a ### heading meaning "Key points to remember" in '
               'the reply language with three to five one-line bullets. Every bullet that states a '
               'fact carries its [n] citation.'),
}

# Asked only of cloud models: costs ~40 output tokens. On the local GPU those tokens are ~15 s,
# so locally the follow-ups come from the book outline instead (app/agents/suggest.py).
FOLLOWUP_NOTE = ('After everything else, on the very last line, write a hidden marker with three short '
                 'follow-up questions (each under 15 words, in the reply language) that a curious reader '
                 'could ask next and that these SOURCES can answer: <<next: first question | second '
                 'question | third question>>. Questions only — no facts, no citations inside the marker. '
                 'Omit the marker for a <<none>> reply.')


def scope_note(state):
    """Tell the model which chapter the reader is studying, when the search was scoped."""
    scope = state.get('scope') or {}
    if not scope or not state.get('scope_applied'):
        return ''
    where = scope.get('label') or 'the selected part of the book'
    return (f'FOCUS: the reader is studying {where}. The sources come from that part of the book; '
            'explain it as a whole when the question asks for an explanation or summary of it.')


def wants_model_followups():
    from app.agents.retriever_agent import answering_provider
    return answering_provider() != 'ollama'


def user_message(state, sources):
    parts = []
    context = conversation_context(state)
    if context:
        parts.append('EARLIER CONVERSATION (context only, not a source):\n' + context)
    parts.append('SOURCES:\n' + sources_block(sources))
    parts.append('QUESTION:\n' + state['user_input'])
    for note in (scope_note(state), STYLE_NOTES.get(state.get('answer_style') or 'detailed', '')):
        if note:
            parts.append(note)
    if wants_model_followups():
        parts.append(FOLLOWUP_NOTE)
    parts.append(f"Answer in {state['detected_language']}, following every rule. "
                 'Remember the hidden first-line marker and a [n] citation after every factual sentence.')
    return '\n\n'.join(parts)


def reviewed_identity(book_id, language):
    """Title and author from the visually reviewed metadata, not from the PDF file name.

    Measured 2026-11-16: the file-name title rendered as "مقدمہ سیرت الرسول 1 1" in answers.
    """
    from app.core.config import ROOT
    try:
        facts = json.loads((ROOT / 'data/book-metadata' / f'{book_id}.json').read_text(encoding='utf-8'))['facts']
    except Exception:
        return '', ''

    def value(name):
        fact = facts.get(name) or {}
        values = fact.get('values') or {}
        return values.get(language) or values.get('English') or fact.get('value') or fact.get('quote') or ''
    return value('title'), value('author')


def book_display_title(book_id, fallback=''):
    """Reviewed short title of a catalogued book ("Creation of Man"), else the given fallback."""
    from app.agents.bibliography import display_title
    from app.ingestion.indexer import catalog
    book = next((b for b in catalog() if b['id'] == book_id), None)
    return display_title(book) if book else fallback


def system_prompt(state, sources):
    names = []
    for book_id in dict.fromkeys(s['window'].get('book_id', '') for s in sources):
        window = next(s['window'] for s in sources if s['window'].get('book_id', '') == book_id)
        title, author = reviewed_identity(book_id, state['detected_language'])
        title = title or window.get('book_title') or 'the book'
        names.append(f'"{title}"' + (f' by {author}' if author else ''))
    return (EXPLAIN_RULES.replace('{book_title}', ' and '.join(names))
            .replace('{language}', state['detected_language']))


WRONG_SCRIPT_LIMIT = .15
SCRIPT_RETRY_NOTE = {
    'Hindi': '\n\nIMPORTANT: your previous answer mixed Urdu/Arabic script into Hindi. Write the ENTIRE '
             'answer in Devanagari script only (ﷺ is the only exception).',
    'Urdu': '\n\nIMPORTANT: your previous answer mixed Devanagari into Urdu. Write the ENTIRE answer in '
            'Urdu script only.',
}


def wrong_script_share(text, language):
    """Share of letters written in the script the reply language does not use."""
    arabic = len(re.findall(r'[؀-ۿ]', (text or '').replace('ﷺ', '')))
    devanagari = len(re.findall(r'[ऀ-ॿ]', text or ''))
    total = arabic + devanagari
    if not total:
        return 0.0
    if language == 'Hindi':
        return arabic / total
    if language == 'Urdu':
        return devanagari / total
    return 0.0


# ------------------------------------------------------------------ parsing
def split_marker(text):
    """Coverage marker and the answer body with every marker removed."""
    match = MARKER.search(text[:80])
    coverage = match.group(1).lower() if match else 'full'
    body = MARKER.sub('', text).strip()
    if coverage == 'none' or not WORD.search(body):
        return 'none', ''
    return coverage, body


def related_from_marker(text, limit):
    """Source numbers the model judged to be on the same subject when it found no answer.

    Measured 2026-11-16: relevance scores could not tell "chain" in an amino-acid chain from a
    bicycle chain, and unrelated pages were shown as related material. The model that has just
    read the passages is the better judge, at no extra call.
    """
    match = MARKER.search(text[:120])
    if not match or not match.group(2):
        return []
    return [n for n in dict.fromkeys(int(x) for x in re.findall(r'\d{1,2}', match.group(2))) if 1 <= n <= limit]


def cited_ids(text, limit):
    ids = []
    for match in CITE.finditer(text):
        for raw in re.findall(r'\d{1,2}', match.group(1)):
            number = int(raw)
            if 1 <= number <= limit and number not in ids:
                ids.append(number)
    return ids


def sentence_units(body):
    """Sentences with their exact position, so audit fixes can be applied in place."""
    units = []
    lines = body.split('\n')
    for line_no, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or set(stripped) <= set('-*_ '):
            continue
        # Initials and abbreviations ("Philip K. Hitti", "Dr. Qadri", "p. 49") are not sentence
        # ends. Measured 2026-11-16: splitting after "K." let an audit fix replace half a
        # sentence and leave "Philip K." dangling. The dot is swapped for a same-width
        # placeholder, so positions still index the original line.
        protected = ABBREVIATION.sub(lambda m: m.group(0)[:-1] + '․', line)
        for match in SENTENCE.finditer(protected):
            raw = line[match.start():match.end()]
            # Remove only a list marker ("- ", "* ", "1. "), never the "**" of bold text.
            text = re.sub(r'^(?:[-*•·]|\d{1,2}[.)])\s+', '', raw.strip()).strip()
            if len(WORD.findall(CITE.sub('', text))) < 3:
                continue
            start = match.start() + raw.index(text[:8]) if text[:8] in raw else match.start()
            units.append({'id': len(units) + 1, 'line': line_no, 'start': start,
                          'end': match.end(), 'text': line[start:match.end()].strip()})
    return units


def plausible_fix(fix, original, seen):
    """Reject an auditor 'fix' that is clearly not a corrected version of the sentence.

    Measured 2026-11-16: a small fallback auditor replaced several different sentences with
    the same meta sentence "This is supported by sources 2, 4, 7, and 12." A correction is
    about as long as the sentence it corrects, is not repeated across sentences, and does not
    talk about the sources instead of the book.
    """
    if not fix:
        return True
    if fix in seen:
        return False
    if len(fix) > 2 * len(original) + 120:
        return False
    if re.search(r'\b(?:supported by|according to) sources?\b|\bsources? \d', fix, re.I):
        return False
    return True


def apply_fixes(body, units, problems, limit):
    by_id = {u['id']: u for u in units}
    edits, seen = {}, set()
    for problem in problems:
        unit = by_id.get(problem.get('id'))
        if unit is None:
            continue
        fix = str(problem.get('fix', '')).strip()
        if not plausible_fix(fix, unit['text'], seen):
            continue
        seen.add(fix)
        if fix and not CITE.search(fix):
            original = cited_ids(unit['text'], limit)
            fix = fix.rstrip() + ''.join(f'[{n}]' for n in original)
        if fix and not cited_ids(fix, limit):
            fix = ''
        edits[unit['id']] = fix
    if not edits:
        return body, 0, 0
    lines = body.split('\n')
    changed = removed = 0
    for unit in sorted((by_id[i] for i in edits), key=lambda u: (u['line'], u['start']), reverse=True):
        line = lines[unit['line']]
        replacement = edits[unit['id']]
        lines[unit['line']] = line[:unit['start']] + replacement + line[unit['end']:]
        if replacement:
            changed += 1
        else:
            removed += 1
    cleaned = []
    for line in lines:
        if re.fullmatch(r'\s*(?:[-*•·]|\d+[.)])?\s*', line) and line.strip():
            continue  # a bullet whose only sentence was removed
        cleaned.append(line.rstrip())
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned)).strip(), changed, removed


def drop_empty_sections(body):
    """A heading left with nothing under it after audit removals is removed too."""
    blocks = re.split(r'(?m)^(?=#{1,6}\s)', body)
    kept = [b for b in blocks if not re.match(r'#{1,6}\s', b) or WORD.search(b.split('\n', 1)[1] if '\n' in b else '')]
    return ''.join(kept).strip()


def page_aliases(sources):
    """Source number -> the first source number from the same book page.

    Two passages of one page used to become two citations, so the reader saw "PDF page 350"
    twice in the source list and two different chips for the same page (measured on cm-en-5).
    """
    first, alias = {}, {}
    for source in sources:
        key = (source['window'].get('book_id'), source['window']['page_start'])
        alias[source['n']] = first.setdefault(key, source['n'])
    return alias


def renumber(body, limit, alias=None):
    """Display numbers 1..k in order of first use; invalid citations removed; one per page."""
    order = []
    alias = alias or {}

    def substitute(match):
        numbers = [int(x) for x in re.findall(r'\d{1,2}', match.group(1)) if 1 <= int(x) <= limit]
        numbers = [alias.get(n, n) for n in numbers]
        out = []
        for number in numbers:
            if number not in order:
                order.append(number)
            label = f'[{order.index(number) + 1}]'
            if label not in out:
                out.append(label)
        return ''.join(out)

    text = CITE.sub(substitute, body)
    text = re.sub(r'(\[\d+\])(?:\s*\1)+', r'\1', text)        # [1] [1] -> [1]
    text = re.sub(r'[ \t]+([.,۔،!?])', r'\1', text)
    return text, order


def best_excerpt(window, sentences):
    """The span of the source that the citing sentences actually draw on."""
    pieces = legible_pieces(window.get('text', '')) or [s['text'] for s in readable_spans(window)]
    if not pieces:
        return ''
    words = {w.lower() for s in sentences for w in WORD.findall(s) if len(w) > 3}
    return max(pieces, key=lambda p: (len(words & {w.lower() for w in WORD.findall(p)}), len(p) > 40))


def build_citations(body, order, sources):
    citations = []
    sentences_for = {}
    for unit in sentence_units(body):
        for display in [int(x) for x in re.findall(r'\[(\d{1,2})\]', unit['text'])]:
            sentences_for.setdefault(display, []).append(CITE.sub('', unit['text']))
    alias = page_aliases(sources)
    for display, source_number in enumerate(order, start=1):
        window = sources[source_number - 1]['window']
        same_page = [s for s in sources if alias[s['n']] == source_number]
        merged = {'text': '\n'.join(s['window'].get('text', '') for s in same_page)}
        excerpt = best_excerpt(merged, sentences_for.get(display, []))
        citations.append({
            'id': display, 'book_id': window['book_id'],
            'book_title': book_display_title(window['book_id'], window['book_title']),
            'page': window['page_start'], 'printed_label': window.get('printed_label'),
            'chapter': window.get('chapter', ''), 'excerpt': display_quote(excerpt, 45),
            'full_support': '\n\n'.join(s['text'] for s in same_page), 'ocr': window.get('ocr', False),
            'corrected': window.get('corrected', False),
            'correction_source': window.get('correction_source', ''),
            'relation': window.get('relation', 'same_concept'),
        })
    return citations


# ------------------------------------------------------------------ audit
async def audit(state, sources, body, provider):
    """One fact-check call. Returns (body, report). Never raises."""
    if provider == 'ollama' and not settings.audit_local:
        return body, {'audited': False, 'reason': 'local model: audit skipped (too slow on this GPU)'}
    if not settings.explain_audit:
        return body, {'audited': False, 'reason': 'audit disabled'}
    units = sentence_units(body)
    if not units:
        return body, {'audited': False, 'reason': 'nothing to audit'}
    limit = len(sources)
    source_numbers = numbers_in(' '.join(s['text'] for s in sources))
    sentences = []
    for u in units:
        item = {'id': u['id'], 'text': CITE.sub('', u['text']).strip(), 'cites': cited_ids(u['text'], limit) or 'none'}
        missing = sorted(numbers_in(item['text']) - source_numbers)
        if missing:
            item['numbers_not_in_sources'] = missing[:8]
        sentences.append(item)
    payload = {
        'sources': [{'n': s['n'], 'pdf_page': s['window']['page_start'], 'text': s['text']} for s in sources],
        'question': state['user_input'],
        'sentences': sentences,
    }
    started = time.monotonic()
    message = json.dumps(payload, ensure_ascii=False)
    result, used, tier, failures = None, '', '', []
    # Two tiers (2026-11-18): a strong judge first, the lite chain as fallback. Measured on 6 final
    # answers: gemini-2.5-flash still flagged 3/62 sentences (4.8%) that the lite audit had passed.
    # Each tier is time-bounded so the reader is never left waiting on a stuck judge (a flash-lite
    # audit once took 53 s; 2.5-flash took 8.5-25 s on 6-17 sentences).
    tiers = ([('audit_strong', settings.strong_audit_timeout)] if settings.strong_audit else []) \
        + [('audit', settings.audit_timeout)]
    for task, timeout in tiers:
        try:
            if task == 'audit_strong' and len(sentences) > STRONG_AUDIT_CHUNK:
                result, used = await chunked_audit(task, payload, timeout)
            else:
                result, used = await asyncio.wait_for(get_chat_model(task).invoke(AUDIT_RULES, message, True),
                                                      timeout=timeout)
            tier = 'strong' if task == 'audit_strong' else 'lite'
            break
        except Exception as exc:
            failures.append(f'{task}: {type(exc).__name__}')
            logger.warning('%s failed: %s', task, type(exc).__name__)
    if result is None:
        return body, {'audited': False, 'reason': 'audit model unavailable: ' + '; '.join(failures)}
    problems = [p for p in (result.get('problems') or []) if isinstance(p, dict)]
    citation_fixes = citations_for_uncited(units, result.get('add_citations'), problems, limit)
    fixed, changed, removed = apply_fixes(body, units, problems + citation_fixes, limit)
    changed -= len(citation_fixes)
    fixed = drop_empty_sections(fixed)
    fixed, unquoted = unquote_unverified(fixed, sources)
    report_ = {'audited': True, 'audit_provider': used, 'audit_tier': tier, 'audit_failures': failures,
               'sentences': len(units), 'changed': changed, 'removed': removed,
               'citations_added': len(citation_fixes), 'unverified_quotes_unquoted': unquoted,
               'number_flags': sum(1 for s in sentences if 'numbers_not_in_sources' in s),
               'issues': [p.get('issue') for p in problems][:40],
               'seconds': round(time.monotonic() - started, 2)}
    return fixed, report_


# Measured 2026-11-18: gemini-2.5-flash judged 22 sentences in 30 s but timed out (40 s) on the 39-
# and 42-sentence detailed answers, which then fell back to the lite judge. Long answers are split
# into chunks judged in PARALLEL (each chunk sees all sources; sentence ids stay global).
STRONG_AUDIT_CHUNK = 18


async def chunked_audit(task, payload, timeout):
    sentences = payload['sentences']
    size = -(-len(sentences) // -(-len(sentences) // STRONG_AUDIT_CHUNK))      # even chunks, each <= 18
    chunks = [sentences[i:i + size] for i in range(0, len(sentences), size)]

    async def one(chunk):
        message = json.dumps({**payload, 'sentences': chunk}, ensure_ascii=False)
        return await asyncio.wait_for(get_chat_model(task).invoke(AUDIT_RULES, message, True), timeout=timeout)
    results = await asyncio.gather(*(one(c) for c in chunks))      # any failure -> lite tier for all
    merged = {'problems': [], 'add_citations': []}
    for result, _ in results:
        for key in merged:
            merged[key].extend(p for p in (result.get(key) or []) if isinstance(p, dict))
    return merged, results[0][1]


# ------------------------------------------------------------------ accuracy guards (2026-11-18)
DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹०१२३४५६७८९', '012345678901234567890123456789')


def numbers_in(text):
    """Numbers in any script (Latin, Arabic-Indic, Urdu, Devanagari digits) as plain strings."""
    return set(re.findall(r'\d+', (text or '').translate(DIGITS)))


def citations_for_uncited(units, proposals, problems, limit):
    """Turn the auditor's add_citations into fixes that append [n] to sentences that had none.

    Only for sentences that really had no citation and were not flagged as a problem; only source
    numbers that exist. The citation goes before the closing full stop so it reads like the rest.
    """
    by_id = {u['id']: u for u in units}
    flagged = {p.get('id') for p in problems}
    out = []
    for proposal in proposals or []:
        if not isinstance(proposal, dict):
            continue
        unit = by_id.get(proposal.get('id'))
        if unit is None or unit['id'] in flagged or cited_ids(unit['text'], limit):
            continue
        cites = [n for n in dict.fromkeys(proposal.get('cites') or []) if isinstance(n, int) and 1 <= n <= limit][:4]
        if not cites:
            continue
        text = unit['text'].rstrip()
        tag = ''.join(f'[{n}]' for n in cites)
        match = re.search(r'[.!?۔।؟]+$', text)
        fixed = text[:match.start()].rstrip() + ' ' + tag + match.group(0) if match else text + ' ' + tag
        out.append({'id': unit['id'], 'issue': 'citation_added', 'fix': fixed})
    return out


QUOTED = re.compile(r'“([^”\n]{20,600})”|"([^"\n]{20,600})"|«([^»\n]{20,600})»|”([^“\n]{20,600})“')
QUOTE_WORDS = 6


def _plain(text):
    text = unicodedata.normalize('NFKD', (text or '').lower())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.findall(r'\w+', text))


def unquote_unverified(body, sources):
    """Text inside quotation marks must be the book's own words.

    A model that translates or paraphrases a passage and puts it in quotation marks presents its own
    words as the book's. Quoted spans of 6+ words that do not occur (after normalising case,
    punctuation and diacritics) in any source are kept as reported speech, without the marks.
    Returns (body, number of quotations un-quoted).
    """
    haystack = _plain(' '.join(s['text'] for s in sources))
    count = 0

    def check(match):
        nonlocal count
        inner = next(g for g in match.groups() if g is not None)
        plain = _plain(CITE.sub('', inner))
        if len(plain.split()) < QUOTE_WORDS or plain in haystack:
            return match.group(0)
        count += 1
        return inner
    return QUOTED.sub(check, body), count


# ------------------------------------------------------------------ node
async def run(state):
    windows = state.get('evidence_windows') or []
    sources = build_sources(windows)
    rounds = state.get('explain_rounds', 0) + 1
    if not sources:
        return {'explanation': {'status': 'none', 'reason': 'no readable source'}, 'explain_rounds': rounds}
    if rounds > 1:
        await draft_reset()
    started = time.monotonic()
    try:
        text, provider = await get_chat_model('explain').stream(system_prompt(state, sources),
                                                                user_message(state, sources))
    except Exception as exc:
        diagnostics.record('explain', failure=type(exc).__name__)
        return {'explanation': {'status': 'failed'}, 'explain_rounds': rounds,
                'errors': state.get('errors', []) + ['Answer unavailable: ' + type(exc).__name__]}
    script_retry = False
    if wrong_script_share(text, state['detected_language']) > WRONG_SCRIPT_LIMIT:
        # Measured 2026-11-16: a flash-lite model answered a Hindi question half in Urdu
        # script. One rewrite in the right script; the cleaner of the two is kept.
        await draft_reset()
        try:
            retry_text, retry_provider = await get_chat_model('explain').stream(
                system_prompt(state, sources),
                user_message(state, sources) + SCRIPT_RETRY_NOTE.get(state['detected_language'], ''))
            if wrong_script_share(retry_text, state['detected_language']) < wrong_script_share(text, state['detected_language']):
                text, provider, script_retry = retry_text, retry_provider, True
        except Exception as exc:
            logger.warning('script retry failed: %s', type(exc).__name__)
    generation_seconds = round(time.monotonic() - started, 2)
    # The follow-up marker is removed BEFORE parsing and auditing: it holds questions, not
    # claims about the book, and must never be audited, cited or shown as answer text.
    text, model_followups = suggest.split_followups(text)
    coverage, body = split_marker(text)
    if coverage == 'none':
        related = [{'book_id': sources[n - 1]['window'].get('book_id'), 'page': sources[n - 1]['window']['page_start']}
                   for n in related_from_marker(text, len(sources))]
        diagnostics.record('explain', round=rounds, coverage='none', provider=provider,
                           seconds=generation_seconds, related=related)
        return {'explanation': {'status': 'none', 'raw': text[:400], 'related': related},
                'provider_used': provider, 'explain_rounds': rounds}
    uncited = [u for u in sentence_units(body) if not cited_ids(u['text'], len(sources))]
    body, audit_report = await audit(state, sources, body, provider)
    body, order = renumber(body, len(sources), page_aliases(sources))
    if not order:
        # Nothing cited survived: this is not a book answer, whatever it says.
        diagnostics.record('explain', round=rounds, coverage='none', reason='no valid citation survived',
                           provider=provider, audit=audit_report)
        return {'explanation': {'status': 'unverified'}, 'provider_used': provider, 'explain_rounds': rounds}
    citations = build_citations(body, order, sources)
    diagnostics.record('explain', round=rounds, coverage=coverage, provider=provider,
                       seconds=generation_seconds, sources=len(sources),
                       cited_pages=[c['page'] for c in citations], uncited_sentences=len(uncited),
                       audit=audit_report, words=len(WORD.findall(body)), script_retry=script_retry,
                       style=state.get('answer_style') or 'detailed', model_followups=len(model_followups))
    followups = suggest.followups_for(model_followups, citations, state['detected_language'])
    return {'explanation': {'status': 'answered', 'markdown': body, 'coverage': coverage,
                            'citations': citations, **audit_report},
            'followups': followups, 'provider_used': provider, 'explain_rounds': rounds}
