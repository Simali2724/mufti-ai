"""Turn fused candidates into a small set of coherent, diverse evidence windows.

A window is a whole parent paragraph (plus neighbouring context when it is short), not a
25-word fragment, so the answering model can actually read an argument. Inside a window the
text is split into numbered spans; the model cites span ids and the code resolves them back
to verbatim source text. That keeps quotes exact without asking a small model to copy
garbled OCR, and it lets the display quote be short while the verified support stays whole.
"""
import re
from app.core.config import settings
from app.ingestion import segment_index

# Sentence ends, line breaks — and the boundary between two bracketed list items. This book
# prints the Charter of Madinah's article titles as one unpunctuated run of "(Title) (Title)
# (Title)", so sentence splitting alone left PDF page 257 as a single 157-token span. A claim
# could then only rest on all fifteen article titles at once, which is why the one article
# that actually concerns the question — "(No Gender Discrimination in Adult Franchise)" —
# could not be cited on its own and the claims drawn from that page were all over-broad.
SENTENCE_SPLIT = re.compile(r'(?<=[۔؟।.!?])\s+|\n+|(?<=\))\s*(?=\()')


ARABIC_SCRIPT = re.compile(r'[؀-ۿ]')
DEVANAGARI = re.compile(r'[ऀ-ॿ]')
MIN_REAL_WORDS = 4
MIN_REAL_SHARE = .3
MAX_STRAY_SHARE = .45
MIN_SCRIPT_CHARS = 12
# How far an unreadable passage is demoted. Demoted, never dropped: this book's Western-writer
# quotations sit in paragraphs that are half real English and half glyph soup, and discarding
# those would lose the material the `west-en-*` questions are about.
UNREADABLE_FACTOR = .4


def readable(text):
    """Is this text something a reader could actually read, or legacy-font glyph soup?

    The source PDF uses legacy InPage fonts, and OCR over them produces runs like
    "vii h V g ujo f ujo f ujo f" and "o F o F i Zi F o F mF o F i i F o o F o m ]m B o".
    Those passed every other check in this pipeline — they are "text", they tokenise, they
    even match queries — and a reader was shown three of them as the book's own words under a
    "Sources" heading. That is worse than saying nothing, so unreadable text is now kept out
    of anything displayed and pushed down in anything ranked.

    Urdu and Hindi are judged by script density and the isolated-single-character signature of
    broken Nastaliq OCR. Latin text is judged by whether real words of four or more letters
    make up a reasonable share of it, which keeps the book's genuine English passages and its
    bracketed heading lists while rejecting glyph runs.
    """
    text = (text or '').strip()
    if not text:
        return False
    from app.ingestion.normalize import tokens as normalise
    words = normalise(text)
    if not words:
        return False
    if ARABIC_SCRIPT.search(text) or DEVANAGARI.search(text):
        stray = sum(1 for word in words if len(word) == 1) / len(words)
        script_chars = len(ARABIC_SCRIPT.findall(text)) + len(DEVANAGARI.findall(text))
        return script_chars >= MIN_SCRIPT_CHARS and stray <= MAX_STRAY_SHARE
    real = [word for word in words if len(word) >= 4 and word.isalpha()]
    return len(real) >= MIN_REAL_WORDS and len(real) / len(words) >= MIN_REAL_SHARE


def readable_spans(window):
    """The spans of this window a reader could actually read."""
    return [span for span in (window.get('spans') or []) if readable(span['text'])]


def short_clean_latin(text):
    """A short line of real English words: a heading ("Tissues and Body Form") or the end of a
    sentence that wrapped ("muscular system."). Measured 2026-11-16 on Creation of Man p.73: both
    were dropped because `readable` needs four words of four letters. Glyph runs such as
    "vii h V g ujo f" fail here: most of their tokens are one or two letters."""
    if ARABIC_SCRIPT.search(text or '') or DEVANAGARI.search(text or ''):
        return False
    words = re.findall(r"[A-Za-zÀ-ɏ’']+", text or '')
    if not 1 <= len(words) <= 12:
        return False
    long_words = [w for w in words if len(w) >= 3]
    return len(long_words) >= max(1, round(.7 * len(words))) and sum(len(w) for w in long_words) >= 6


def name_fragment(text):
    """A short piece made of name words and initials, not glyph soup."""
    words = (text or '').split()
    if len(words) <= 2:
        return True
    real = [w for w in words if len(w.strip('.,;:()')) >= 3 and w.strip('.,;:()').isalpha()]
    return len(words) <= 8 and len(real) / len(words) >= .5


SCRIPT_RUN = re.compile(r'[؀-ۿ][؀-ۿ\s\d()\[\]«»"\'.,:;\-–]*|[ऀ-ॿ][ऀ-ॿ\s\d().,:;\-–]*|[^؀-ۿऀ-ॿ]+')


def legible_pieces(text):
    """Every line or sentence of a passage that is readable on its own, in reading order.

    `readable_spans` judges whole spans, and `spans_for` merges short lines forward, so a
    clean English sentence merged with a line of Urdu reference noise was judged as broken
    Urdu and lost. Measured 2026-11-16 on PDF page 375: "Leon Duguit 1859-1928 Sovereignty is
    an essential attribute of the state was a myth to be discarded." never reached the model,
    which then correctly said the passage did not answer the question about Duguit. Here each
    line is judged alone, and a mixed-script line is split by script, so one readable sentence
    survives the noise beside it. Unreadable pieces are still never returned.
    """
    pieces = []
    for line in re.split(r'\n+', text or ''):
        clean = re.sub(r'\s+', ' ', line).replace('‏', '').replace('‎', '').strip()
        parts = [p for p in SENTENCE_SPLIT.split(line) if p and p.strip()]
        # Keep a readable line whole when its only unreadable pieces are name fragments such
        # as the initials in "Cardinal R. W. Southern" or "Ronald L. Nettler". Measured
        # 2026-11-16 on page 51: per-sentence judging dropped "Cardinal R." and "W." and the
        # surname after "Ronald L.", so writers the book quotes lost their names — and names
        # are what attribution rests on. A line carrying a real glyph run still fails this.
        if clean and readable(clean) and all(name_fragment(p) for p in parts if not readable(p)):
            pieces.append(clean)
            continue
        for part in parts:
            part = re.sub(r'\s+', ' ', part or '').replace('‏', '').replace('‎', '').strip()
            if not part:
                continue
            if readable(part) or short_clean_latin(part):
                pieces.append(part)
                continue
            for run in SCRIPT_RUN.findall(part):
                run = run.strip(' ,;:()')
                if run and readable(run):
                    pieces.append(run)
    return pieces


def estimate_tokens(text):
    """Rough budget estimate. Urdu/Arabic script costs far more tokens per character."""
    ascii_chars = sum(c.isascii() for c in text)
    return int(ascii_chars / 3.6 + (len(text) - ascii_chars) / 1.4) + 1


def relevance(candidate):
    """Blend the retrievers instead of letting dense similarity veto an exact-word hit."""
    dense = max(0.0, min(1.0, candidate.get('dense_score', 0) or 0))
    lexical = max(0.0, min(1.0, candidate.get('lexical_score', 0) or 0))
    fusion = min(1.0, (candidate.get('rrf', 0) or 0) * 8)
    return round(.45 * dense + .35 * lexical + .20 * fusion, 4)


# How far a passage is demoted when the question named a reviewed concept and the passage
# does not carry any surface form of it. Demoted, never dropped: it can still be selected
# once the on-concept material is exhausted, and it is still shown as related reading.


def concept_relation(candidate, guard):
    """Is this passage about the concept the question named, or an adjacent one?

    Measured on the gender-equality question: four of the six evidence windows were Charter
    of Madinah pages about constitutional equality and women's protection rights. They were
    retrieved on dense similarity, they carry no gender-equality wording in any script, and
    the local model duly drafted six claims from them that verification then rejected one by
    one. Those four windows crowded out page 50's own surrounding paragraphs. They are still
    offered to the reader as related material; they are no longer the first thing a small
    model is asked to explain.
    """
    if not guard:
        return candidate.get('relation', 'same_concept')
    from app.agents.verifier_agent import mentions_concept
    # Three-way, not two-way, and the distinction was forced by two measured cases pulling in
    # opposite directions:
    #   gender equality  - the pages crowding the budget carried "آئینی مساوات کا حق", a
    #                      DIFFERENT reviewed concept. They are genuine distractors and the
    #                      drafter wrote six rejected claims from them.
    #   west-en-2        - the pages being held back carried no reviewed concept wording at
    #                      all, only because the lexicon has no entry for their subject. They
    #                      were the right pages, and demoting them lost the case.
    # So only a passage carrying a RIVAL reviewed concept is demoted and capped. A passage
    # the lexicon simply says nothing about is left alone, because absence from a hand-written
    # lexicon is not evidence that a passage is off topic.
    # The clean outline title counts as well as the body text. On this book the body is
    # degraded OCR, so a reviewed Urdu surface form often matches only the title: PDF page
    # 280's body reads "آینی مساوات" while its section title reads "آئینی مساوات". Including
    # the title is what lets a rival concept be recognised by name rather than missed.
    text = ' '.join(filter(None, [candidate.get('parent_text') or candidate.get('text', ''),
                                  section_title(candidate)]))
    if mentions_concept(text, guard['asked']):
        return 'same_concept'
    if any(mentions_concept(text, forms) for _, forms in guard['competing']):
        return 'related_concept'
    return candidate.get('relation', 'same_concept')


def section_title(candidate):
    """Clean chapter/section heading for this candidate's page, from the persisted tree."""
    from app.ingestion import book_tree
    located = book_tree.locate(candidate.get('book_id', ''), candidate.get('page_start', 0) or 0)
    return ' · '.join(filter(None, [located.get('chapter', ''), located.get('section', '')]))


def passes_floor(candidate):
    """Keep a candidate that is convincing on EITHER signal."""
    return (candidate.get('dense_score', 0) >= settings.rerank_threshold
            or candidate.get('lexical_score', 0) >= settings.lexical_floor
            or candidate.get('graph_hits', 0) >= 2
            # A segment of the small section the reader explicitly chose to study (scope
            # sweep, app/retrieval/hybrid.py). It ranks below real matches on relevance.
            or candidate.get('scope_hits', 0) >= 1)


def rank(candidates, guard=None):
    scored = []
    for candidate in candidates:
        relation = concept_relation(candidate, guard)
        score = relevance(candidate)
        if guard and relation != 'same_concept':
            score = round(score * settings.off_concept_factor, 4)
        legible = readable(candidate.get('parent_text') or candidate.get('text', ''))
        if not legible:
            score = round(score * UNREADABLE_FACTOR, 4)
        scored.append({**candidate, 'relevance': score, 'relation': relation,
                       'readable': legible})
    kept = [c for c in scored if passes_floor(c)]
    return sorted(kept or scored[:settings.evidence_windows], key=lambda c: c['relevance'], reverse=True)


HEADING_CHARS = 200
HEADING_WINDOW_CAP = 1800


def window_text(candidate):
    """Parent paragraph, extended with a neighbour when the parent is too short to stand alone."""
    parent = candidate.get('parent_text') or candidate.get('text', '')
    if len(parent) >= 420 or not candidate.get('parent_id'):
        return parent
    neighbours = segment_index.page_parents(candidate.get('book_id', ''), candidate.get('page_start', 0))
    if parent in neighbours:
        position = neighbours.index(parent)
        extra = [n for n in neighbours[max(0, position - 1):position + 2] if n != parent]
        # A bare heading matched the question, so the paragraph under it IS the answer. Measured
        # 2026-11-16: "Tissues and Body Form" matched Creation of Man p.73's 113-char heading and the
        # 821-char body was skipped by the 900-char cap, so the model saw only the heading.
        cap = HEADING_WINDOW_CAP if len(parent) < HEADING_CHARS else 900
        for piece in extra:
            if len(parent) + len(piece) > cap:
                break
            parent = f'{parent}\n{piece}' if neighbours.index(piece) > position else f'{piece}\n{parent}'
    return parent


def spans_for(text, min_words=4):
    """Numbered verbatim spans. Short lines merge forward so a span carries real meaning."""
    pieces = [p.strip() for p in SENTENCE_SPLIT.split(text) if p.strip()]
    spans, buffer = [], ''
    for piece in pieces:
        buffer = (buffer + ' ' + piece).strip() if buffer else piece
        if len(buffer.split()) >= min_words and len(buffer) >= 24:
            spans.append(buffer)
            buffer = ''
    if buffer:
        if spans:
            spans[-1] = (spans[-1] + ' ' + buffer).strip()
        else:
            spans.append(buffer)
    return [{'span_id': i + 1, 'text': re.sub(r'\s+', ' ', s).replace('‏', '').replace('‎', '')}
            for i, s in enumerate(spans[:24])]


def select(candidates, token_budget=None, max_windows=None, exclude_pages=(), concepts=()):
    """Choose diverse, de-duplicated windows that fit the model's context budget."""
    from collections import Counter
    from app.agents.verifier_agent import concept_guard
    token_budget = token_budget or settings.evidence_token_budget
    max_windows = max_windows or settings.evidence_windows
    guard = concept_guard(concepts) or None
    windows, used_pages, used_parents, spent, off_concept = [], Counter(), set(), 0, 0
    # Candidates that ONLY the adjacent-concept cap turned away. They are reconsidered in a
    # second pass once the on-concept material is exhausted, because that cap exists to stop
    # them crowding out better evidence, never to leave the model with less evidence than it
    # could have had. Measured regression that forced this: on "What do Western writers say
    # about the simplicity of the Prophet's life" a hard cap cut the evidence from eight
    # windows to three and lost the reviewed pages — a false refusal manufactured by a guard.
    deferred = []

    def consider(candidate, enforce_cap):
        nonlocal spent, off_concept
        page = candidate.get('page_start')
        parent_id = candidate.get('parent_id') or candidate['id']
        if parent_id in used_parents or page in exclude_pages:
            return
        # One window per page first, so a single noisy page cannot fill the whole budget —
        # except that a page genuinely about the question's concept may contribute a second
        # paragraph straight away. On the gender-equality question page 50's English quote
        # was the only thing taken from that page while its own Urdu framing paragraphs,
        # which introduce the quote, lost their place to unrelated garbled pages.
        cap = 2 if (guard and candidate['relation'] == 'same_concept') else 1
        if used_pages[page] >= cap and len(windows) < max_windows - 1:
            return
        if (enforce_cap and guard and candidate['relation'] != 'same_concept'
                and off_concept >= settings.evidence_related_windows):
            deferred.append(candidate)
            return
        text = window_text(candidate)
        if not text.strip():
            return
        cost = estimate_tokens(text)
        if spent + cost > token_budget and windows:
            return
        used_parents.add(parent_id)
        used_pages[page] += 1
        off_concept += candidate['relation'] != 'same_concept'
        spent += cost
        windows.append({
            'source_id': len(windows) + 1,
            'chunk_id': candidate['id'],
            'parent_id': parent_id,
            'book_id': candidate.get('book_id', ''),
            'book_title': candidate.get('book_title', ''),
            'page_start': page,
            'page_end': candidate.get('page_end', page),
            'printed_label': candidate.get('printed_label'),
            # The OCR'd `chapter` field held whatever text topped the page, including
            # running headers and the publisher's address. The outline title is correct.
            'chapter': section_title(candidate) or candidate.get('chapter', ''),
            'ocr': bool(candidate.get('ocr')),
            'corrected': bool(candidate.get('corrected')),
            'correction_source': candidate.get('correction_source', ''),
            'relation': candidate['relation'],
            'readable': candidate.get('readable', True),
            'relevance': candidate['relevance'],
            'dense_score': round(candidate.get('dense_score', 0) or 0, 4),
            'lexical_score': round(candidate.get('lexical_score', 0) or 0, 4),
            'matched_queries': candidate.get('matched_queries', [])[:6],
            'text': text,
            'spans': spans_for(text),
            'tokens': cost,
        })

    for candidate in rank(candidates, guard):
        if len(windows) >= max_windows:
            break
        consider(candidate, enforce_cap=True)
    # Second pass: the adjacent-concept passages held back above, now that nothing better is
    # competing for the budget. Order is preserved, so they still rank below the on-concept
    # material rather than replacing it.
    for candidate in deferred:
        if len(windows) >= max_windows:
            break
        consider(candidate, enforce_cap=False)
    recovered = recover_siblings(windows, guard, token_budget - spent, max_windows - len(windows))
    windows += recovered
    spent += sum(w['tokens'] for w in recovered)
    return windows, {'selected_pages': [w['page_start'] for w in windows], 'tokens': spent,
                     'token_budget': token_budget,
                     'recovered_siblings': [w['page_start'] for w in recovered]}


def recover_siblings(windows, guard, budget_left, slots):
    """Other paragraphs of an already-selected page that carry the question's concept.

    Retrieval scores one paragraph at a time, so the paragraph that introduces a quotation
    can rank far below the quotation itself and never reach the model — on this book page
    50's Urdu framing ("a Western thinker writes ...") ranked 24th while its English quote
    ranked 1st. Recovering it is parent/neighbour recovery, not a new search: the page is
    already selected, and only a sibling that carries a reviewed surface form of the asked
    concept is taken, so this cannot drag in unrelated text from a busy page.
    """
    if not guard or slots <= 0 or budget_left <= 0:
        return []
    from app.agents.verifier_agent import mentions_concept
    seen = {canonical_text(w['text']) for w in windows}
    out = []
    for window in [w for w in windows if w['relation'] == 'same_concept']:
        for text in segment_index.page_parents(window['book_id'], window['page_start']):
            key = canonical_text(text)
            if key in seen or not mentions_concept(text, guard['asked']):
                continue
            cost = estimate_tokens(text)
            if cost > budget_left or len(out) >= slots:
                continue
            seen.add(key)
            budget_left -= cost
            out.append({**window, 'source_id': len(windows) + len(out) + 1, 'text': text,
                        'spans': spans_for(text), 'tokens': cost, 'relation': 'same_concept',
                        'relevance': window['relevance'], 'recovered': 'same_page_context'})
    return out


def canonical_text(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def resolve_spans(window, span_ids):
    """Exact source text for the cited spans, contiguous ones joined in reading order."""
    chosen = [s for s in window['spans'] if s['span_id'] in set(span_ids or [])]
    if not chosen:
        return ''
    return ' '.join(s['text'] for s in sorted(chosen, key=lambda s: s['span_id']))


def display_quote(text, max_words=30):
    """Short quote for the citation strip. The verified support stays the full span."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words]).rstrip(' ,;:') + ' …'
