"""Render full, partial and not-found coverage distinctly, with honest failure reporting."""
from app.core import diagnostics
from app.core.language import (NOT_FOUND, GREETINGS, NEEDS_TOPIC, REFUSALS, DISCLAIMERS, PARTIAL_INTRO, MISSING_HEADING,
                               RELATED_HEADING, SOURCES_HEADING, NO_DIRECT_ANSWER, QUOTA_EXHAUSTED,
                               EXPLANATION_UNVERIFIED, EXTRACTION_PROBLEM, OUT_OF_LIBRARY, NOT_IN_LIBRARY,
                               PROVIDER_UNAVAILABLE, SEARCH_UNAVAILABLE)
from app.retrieval.evidence import display_quote, readable_spans

SERVICE_UNAVAILABLE = PROVIDER_UNAVAILABLE


def source_line(citation, language):
    label = ''
    if citation.get('printed_label') and citation['printed_label'] != citation['page']:
        label = f" ({'printed page'  if language == 'English' else 'printed'} {citation['printed_label']})"
    return f"[{citation['id']}] {citation['book_title']} · PDF page {citation['page']}{label} — «{citation['excerpt']}»"


def build_citations(draft, windows):
    by_source, citations = {}, []
    for claim in draft.get('claims', []):
        source_id = claim['source_id']
        if source_id not in by_source:
            window = next((w for w in windows if w['source_id'] == source_id), None)
            if window is None:
                continue
            by_source[source_id] = len(citations) + 1
            citations.append({
                'id': by_source[source_id], 'book_id': window['book_id'], 'book_title': window['book_title'],
                'page': window['page_start'], 'printed_label': window.get('printed_label'),
                'chapter': window.get('chapter', ''), 'excerpt': display_quote(claim['support']),
                'full_support': claim['support'], 'ocr': window.get('ocr', False),
                'corrected': window.get('corrected', False),
                'correction_source': window.get('correction_source', ''),
                'relation': window.get('relation', 'same_concept'),
            })
        claim['citation_id'] = by_source[source_id]
    return citations


# A passage is offered as "related" only when it really shares the question's subject: some
# keyword overlap, or strong meaning similarity. Measured 2026-11-16: "write me a code of adding
# two number in C" pulled pages scoring dense 0.47-0.51 with zero keyword overlap, and showing them
# as related material looked like hallucination. Every genuine book question in the traces had
# lexical >= 0.4 or dense >= 0.52 on its top windows.
RELATED_MIN_LEXICAL = .3
RELATED_MIN_DENSE = .58


def truly_related(window):
    return (window.get('lexical_score', 0) >= RELATED_MIN_LEXICAL
            or window.get('dense_score', 0) >= RELATED_MIN_DENSE)


def title_of(window):
    from app.agents.explain_agent import book_display_title
    return book_display_title(window.get('book_id', ''), window.get('book_title', ''))


def library_names():
    from app.agents.bibliography import display_title
    from app.ingestion.indexer import catalog
    return ' · '.join(f'“{display_title(b)}”' for b in catalog()) or 'your books'


def related_block(windows, used_pages, language, limit=3, concepts=(), trust=False):
    """`trust`: the windows were already chosen by the model as same-subject material."""
    items = [w for w in windows
             if w['page_start'] not in used_pages and readable_spans(w)
             and (trust or truly_related(w))][:limit]
    if not items:
        return '', []
    lines = [RELATED_HEADING[language]]
    related = []
    for index, window in enumerate(items, start=1):
        excerpt = display_quote(best_span(window, concepts))
        if not excerpt:
            continue
        lines.append(f"· {title_of(window)} · PDF page {window['page_start']} — «{excerpt}»")
        related.append({'id': index, 'book_id': window['book_id'], 'book_title': title_of(window),
                        'page': window['page_start'], 'printed_label': window.get('printed_label'),
                        'chapter': window.get('chapter', ''), 'excerpt': excerpt,
                        'ocr': window.get('ocr', False), 'relation': window.get('relation', 'same_concept')})
    return '\n'.join(lines), related


def failure_reason(state):
    """Separate a service problem from a genuine absence of evidence in the book."""
    if state.get('retrieval_failed'):
        return 'retrieval_unavailable'
    if state.get('verification_report', {}).get('service_failure'):
        return 'provider_unavailable'
    if any('Answer unavailable' in e for e in state.get('errors', [])):
        return 'provider_quota_exhausted' if diagnostics.quota_exhausted() else 'provider_unavailable'
    windows = state.get('evidence_windows') or []
    if not windows:
        return 'no_matching_passages'
    # The pages that matched exist, but their extracted text is legacy-font OCR noise. That is
    # a problem with this book's extraction, not with the model and not an absence of evidence,
    # and the brief requires it to be its own outcome. Without this the reader was shown runs
    # like "vii h V g ujo f ujo f ujo f" as the book's own words.
    if not any(readable_spans(window) for window in windows):
        return 'extraction_problem'
    if (state.get('explanation') or {}).get('status') == 'unverified':
        return 'explanation_unverified'
    if not state.get('draft_answer', {}).get('claims') and state.get('verification_report', {}).get('rejected'):
        # Distinguish "the model could not produce a verifiable explanation of material the
        # book clearly carries" from "the book's material does not cover this". The brief
        # requires these to be separate outcomes, and conflating them is how a reader ends up
        # being told the book is silent about something that is printed on page 50.
        on_concept = [w for w in state.get('evidence_windows') or []
                      if w.get('relation') == 'same_concept']
        return 'explanation_unverified' if on_concept else 'insufficient_evidence_after_search'
    return 'insufficient_coverage'


def best_span(window, concepts):
    """The span of this window that actually concerns the question, not merely its first.

    Page 257's article list splits into fourteen spans, of which exactly one is about gender.
    Showing span 1 — "(Conditional Superordination of State)" — as the excerpt would hand the
    reader the least relevant line on a page that does carry the clause they asked about.
    """
    # Only spans a reader could actually read. A reader was once shown three excerpts reading
    # "vii h V g ujo f ujo f ujo f" under a Sources heading, presented as the book's own
    # words; legacy-font OCR noise must never be offered as a quotation from the book.
    spans = readable_spans(window)
    if not spans:
        return ''
    if concepts:
        from app.agents.verifier_agent import concept_forms, mentions_concept
        forms = concept_forms(concepts)
        match = next((s['text'] for s in spans if mentions_concept(s['text'], forms)), '')
        if match:
            return match
    return spans[0]['text']


def excerpt_block(windows, language, limit=3, concepts=()):
    """Faithful source excerpts, clearly labelled as excerpts and not as an explanation."""
    items = [w for w in windows
             if w.get('relation') == 'same_concept' and readable_spans(w)][:limit]
    lines, excerpts = [SOURCES_HEADING[language]], []
    for index, window in enumerate(items, start=1):
        text = best_span(window, concepts)
        if not text:
            continue
        excerpts.append({'id': index, 'book_id': window['book_id'], 'book_title': window['book_title'],
                         'page': window['page_start'], 'printed_label': window.get('printed_label'),
                         'chapter': window.get('chapter', ''), 'excerpt': display_quote(text, 60),
                         'full_support': window['text'], 'ocr': window.get('ocr', False),
                         'relation': window.get('relation', 'same_concept')})
        lines.append(source_line(excerpts[-1], language))
    return ('\n'.join(lines) if excerpts else ''), excerpts


def run(state):
    language = state['detected_language']
    intent = state.get('intent')
    windows = state.get('evidence_windows') or []
    draft = state.get('draft_answer', {}) or {}
    citations, related, grounded, coverage = [], [], False, 'none'
    reason, answer_format, verification = '', 'text', ''
    if intent == 'needs_topic':
        answer, reason = NEEDS_TOPIC[language], 'needs_topic'
    elif intent == 'smalltalk':
        answer = GREETINGS[language]
    elif intent == 'unsafe':
        answer, reason = REFUSALS[language], 'unsafe'
    elif intent == 'out_of_scope':
        answer, reason = OUT_OF_LIBRARY[language].format(books=library_names()), 'out_of_scope'
    elif (state.get('explanation') or {}).get('status') == 'answered':
        explanation = state['explanation']
        coverage = explanation.get('coverage', 'full')
        grounded = True
        citations = explanation.get('citations', [])
        answer = explanation['markdown']
        if intent == 'fiqh_masala' and DISCLAIMERS[language] not in answer:
            answer += '\n\n> ' + DISCLAIMERS[language]
        reason = 'partial_coverage' if coverage == 'partial' else ''
        answer_format = 'markdown'
        verification = 'audited' if explanation.get('audited') else 'citations_checked'
        if coverage == 'partial':
            _, related = related_block(windows, {c['page'] for c in citations}, language,
                                       concepts=state.get('matched_concepts') or ())
    elif state.get('verification_report', {}).get('passed'):
        verification = 'claims_verified'
        coverage = draft.get('coverage', 'full')
        grounded = True
        citations = build_citations(draft, windows)
        blocks = []
        if coverage == 'partial':
            blocks.append(PARTIAL_INTRO[language])
        for section in draft.get('sections', []):
            heading = str(section.get('heading', '')).strip()
            lines = [f"{claim['text'].strip()} [{claim['citation_id']}]" for claim in section['claims']]
            blocks.append((heading + '\n' if heading else '') + '\n'.join(lines))
        missing = [str(m).strip() for m in draft.get('missing_aspects', []) if str(m).strip()]
        if coverage == 'partial' and missing:
            blocks.append(MISSING_HEADING[language] + '\n' + '\n'.join('· ' + m for m in missing))
        if intent == 'fiqh_masala':
            blocks.append(DISCLAIMERS[language])
        if coverage == 'partial':
            text, related = related_block(windows, {c['page'] for c in citations}, language,
                                          concepts=state.get('matched_concepts') or ())
            if text:
                blocks.append(text)
        blocks.append(SOURCES_HEADING[language] + '\n'
                      + '\n'.join(source_line(c, language) for c in citations))
        answer = '\n\n'.join(b for b in blocks if b)
        reason = 'partial_coverage' if coverage == 'partial' else ''
    else:
        reason = failure_reason(state)
        if reason == 'retrieval_unavailable':
            answer = SEARCH_UNAVAILABLE[language]
        elif reason == 'provider_quota_exhausted':
            answer = QUOTA_EXHAUSTED[language] + '\n\n' + PROVIDER_UNAVAILABLE[language]
        elif reason == 'provider_unavailable':
            answer = PROVIDER_UNAVAILABLE[language]
        elif reason == 'no_matching_passages':
            answer = NOT_FOUND[language]
        elif reason == 'extraction_problem':
            # Page numbers only, with links. Never the text itself: it is unreadable, and
            # printing it as a quotation is how this failure reached a reader in the first place.
            answer = EXTRACTION_PROBLEM[language]
            pages = sorted({w['page_start'] for w in windows})[:5]
            related = [{'id': i, 'book_id': w['book_id'], 'book_title': w['book_title'],
                        'page': w['page_start'], 'printed_label': w.get('printed_label'),
                        'chapter': w.get('chapter', ''),
                        'excerpt': '(text on this page did not extract readably)',
                        'ocr': w.get('ocr', False), 'relation': w.get('relation', 'related_concept')}
                       for i, w in enumerate(
                           [next(x for x in windows if x['page_start'] == p) for p in pages], start=1)]
            if pages:
                listing = '\n'.join(f"· {w['book_title']} · PDF page {w['page']}" for w in related)
                answer += '\n\n' + RELATED_HEADING[language] + '\n' + listing
        elif reason == 'explanation_unverified':
            # The book DOES carry material on this; the model could not turn it into a claim
            # that survived verification. Give the reader the book's own words, say plainly
            # that this is not a generated explanation, and never call it an absence.
            answer = EXPLANATION_UNVERIFIED[language]
            text, related = excerpt_block(windows, language,
                                           concepts=state.get('matched_concepts') or ())
            if text:
                answer += '\n\n' + text
        else:
            explanation = state.get('explanation') or {}
            candidates = windows
            if explanation.get('status') == 'none':
                # The answering model read these passages and named the ones on the same
                # subject (possibly none). Its judgement replaces score thresholds here.
                chosen = {(r.get('book_id'), r.get('page')) for r in explanation.get('related') or []}
                candidates = [w for w in windows if (w.get('book_id'), w['page_start']) in chosen]
            text, related = related_block(candidates, set(), language,
                                          concepts=state.get('matched_concepts') or (),
                                          trust=explanation.get('status') == 'none')
            if text:
                answer = NO_DIRECT_ANSWER[language] + '\n\n' + text
            else:
                # Nothing in the library is even about this subject: say so plainly, name the
                # books, and show no passages rather than unrelated ones.
                answer, reason = NOT_IN_LIBRARY[language].format(books=library_names()), 'not_in_library'
    from app.llm.preferences import request_trace
    trace = list(request_trace.get() or [])
    event = next((item for item in reversed(trace) if item['task'] in ('answer', 'explain')), trace[-1] if trace else {})
    report = state.get('verification_report', {})
    followups = next_questions(state, reason, grounded, citations, related, language)
    turn = {'question': state['user_input'], 'answer': answer, 'language': language, 'citations': citations,
            'related': related, 'grounded': grounded, 'coverage': coverage,
            'provider_used': state.get('provider_used', 'none'), 'model_used': event.get('model', ''),
            'fallback_used': event.get('fallback', False), 'execution': trace, 'reason_code': reason,
            'missing_aspects': draft.get('missing_aspects', []) if grounded else [],
            'rejected_claims': len(report.get('rejected', [])),
            'answer_format': answer_format, 'verification': verification,
            'followups': followups, 'answer_style': state.get('answer_style') or 'detailed'}
    diagnostics.record('outcome', reason_code=reason, coverage=coverage, grounded=grounded,
                       citation_pages=[c['page'] for c in citations],
                       related_pages=[r['page'] for r in related])
    history = state.get('history', []) + [turn]
    return {'final_answer': answer, 'reason_code': reason, 'citations': citations, 'related': related,
            'grounded': grounded, 'coverage': coverage, 'history': history[-10:],
            'missing_aspects': turn['missing_aspects'], 'answer_format': answer_format,
            'verification': verification, 'followups': followups}


def next_questions(state, reason, grounded, citations, related, language):
    """Clickable "ask next" suggestions for every outcome (app/agents/suggest.py).

    An answer: the model's own follow-ups, topped up from the outline of the cited pages.
    No subject named / nothing in the library: chapter topics, so the reader learns what the
    books actually contain instead of guessing again. A partial or related-only result: the
    sections the related pages belong to. Errors get none: retrying is the right action there.
    """
    from app.agents import suggest
    try:
        if grounded:
            return state.get('followups') or suggest.from_outline(citations, language)
        if reason in ('needs_topic', 'not_in_library', 'out_of_scope', 'no_matching_passages') \
                or state.get('intent') == 'smalltalk':
            return suggest.starter_topics(language, limit=3)
        if reason in ('insufficient_coverage', 'insufficient_evidence_after_search',
                      'explanation_unverified', 'partial_coverage'):
            return suggest.from_outline(related, language)
    except Exception:  # suggestions are a convenience; never fail an answer over them
        return []
    return []
