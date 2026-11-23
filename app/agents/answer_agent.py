"""Draft an answer from whole evidence windows, with explicit full/partial/none coverage."""
import json
from app.core import diagnostics
from app.core.config import settings
from app.llm.prompts import ANSWER_RULES
from app.llm.router import get_chat_model
from app.retrieval.evidence import resolve_spans


def evidence_payload(windows):
    """One entry per window: the passage AS its numbered spans, in reading order.

    The spans concatenated are the passage, so sending both doubled the evidence tokens and
    made the measured context roughly twice the budget evidence.select had computed — on a
    small local context window that pushed real passages out of the prompt.
    """
    from app.agents.verifier_agent import quoted_authorities
    payload = []
    for window in windows:
        entry = {
            'source_id': window['source_id'],
            'pdf_page': window['page_start'],
            'section': window['chapter'],
            'relation': window['relation'],
            'passage_spans': [{'span_id': s['span_id'], 'text': s['text']} for s in window['spans']],
        }
        # Name the outside writers this passage credits, so the model does not have to infer
        # them from a garbled citation line. A claim resting on their quoted view must say so,
        # and verification rejects it otherwise.
        if window['relation'] != 'same_concept':
            # Retrieved on similarity alone, carrying no wording of the concept the question
            # named. It is context, not an answer, and saying so stops a small model drafting
            # confident claims about an adjacent right that verification will then reject.
            entry['caution'] = ('This passage does not use the wording of the concept asked '
                                'about. Treat it as background; do not build a claim about '
                                'the asked concept on it.')
        writers = sorted(quoted_authorities(window['text']))
        if writers:
            entry['quotes_these_outside_writers'] = writers
            entry['attribution_required'] = (
                'This passage quotes ' + ', '.join(writers)
                + '. Any claim you draw from it must name them; it is not the book\'s own conclusion.')
        payload.append(entry)
    return payload


MAX_CLAIM_CHARS = 700
MAX_HEADING_CHARS = 90
MAX_MISSING_ASPECTS = 5
MAX_MISSING_ASPECT_CHARS = 140


def attach_support(result, windows):
    """Resolve every cited span back to verbatim source text; drop claims that cite nothing real.

    This is also where the schema bounds are enforced. The grammar sent to a local model has
    its length and count bounds stripped, because expanding them into GBNF cut generation to
    a third of its speed (see app/llm/structured.py), so the section count, claim count,
    heading length and claim length are applied here instead of being trusted from the model.
    """
    by_id = {w['source_id']: w for w in windows}
    claims, claim_id = [], 0
    sections = [s for s in (result.get('sections') or []) if isinstance(s, dict)]
    for section in sections[:settings.answer_max_sections]:
        section['heading'] = str(section.get('heading', ''))[:MAX_HEADING_CHARS]
        kept = []
        for claim in (section.get('claims') or []):
            if not isinstance(claim, dict):
                continue
            if len(claims) >= settings.answer_max_claims:
                break
            window = by_id.get(claim.get('source_id'))
            if window is None:
                continue
            span_ids = [s for s in (claim.get('span_ids') or []) if isinstance(s, int)]
            support = resolve_spans(window, span_ids)
            if not support:
                continue
            text = str(claim.get('text', ''))[:MAX_CLAIM_CHARS]
            claim_id += 1
            claim.update(text=text, claim_id=claim_id, support=support, span_ids=span_ids,
                         page=window['page_start'], printed_label=window.get('printed_label'),
                         section_heading=section['heading'])
            kept.append(claim)
            claims.append(claim)
        section['claims'] = kept
    result['sections'] = [s for s in sections[:settings.answer_max_sections] if s.get('claims')]
    result['claims'] = claims
    result['missing_aspects'] = [str(m)[:MAX_MISSING_ASPECT_CHARS]
                                 for m in (result.get('missing_aspects') or [])
                                 if str(m).strip()][:MAX_MISSING_ASPECTS]
    if not claims and result.get('coverage') != 'none':
        result['coverage'] = 'none'
    return result


async def run(state):
    windows = state.get('evidence_windows') or []
    if not windows:
        return {'draft_answer': {'coverage': 'none', 'sections': [], 'claims': [], 'missing_aspects': []}}
    payload = {
        'question': state['user_input'],
        'reply_language': state['detected_language'],
        'sources': evidence_payload(windows),
        'feedback': state.get('verification_report', {}).get('feedback', ''),
    }
    try:
        result, provider = await get_chat_model('answer').invoke(
            ANSWER_RULES, json.dumps(payload, ensure_ascii=False), True)
        if not isinstance(result, dict):
            raise ValueError('Invalid answer payload')
        result.setdefault('coverage', 'none')
        result.setdefault('sections', [])
        result.setdefault('missing_aspects', [])
        result = attach_support(result, windows)
        diagnostics.record('answer', coverage=result['coverage'], claims=len(result['claims']),
                           cited_pages=sorted({c['page'] for c in result['claims']}),
                           missing_aspects=result.get('missing_aspects', []), provider=provider)
        return {'draft_answer': result, 'provider_used': provider}
    except Exception as exc:
        diagnostics.record('answer', failure=type(exc).__name__)
        return {'draft_answer': {'coverage': 'none', 'sections': [], 'claims': [], 'missing_aspects': []},
                'errors': state.get('errors', []) + ['Answer unavailable: ' + type(exc).__name__]}
