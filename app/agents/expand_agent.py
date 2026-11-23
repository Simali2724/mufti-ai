"""Second search for the subtopics the first round missed.

Runs before the app is allowed to say the book has no answer. Queries come from the model's
own list of missing aspects plus the reviewed concept lexicon, and the pages already shown to
the answering model are excluded so the second round brings genuinely new evidence.
"""
import json
import time
from app.core import diagnostics
from app.llm.router import get_chat_model
from app.llm.prompts import SUBTOPIC_RULES
from app.retrieval.hybrid import search
from app.retrieval.evidence import select
from app.retrieval.query_expansion import concept_variants
from app.agents.retriever_agent import token_budget, window_count


async def subtopic_queries(state):
    missing = [str(m) for m in (state.get('draft_answer', {}) or {}).get('missing_aspects', []) if str(m).strip()]
    queries = []
    for aspect in missing[:4]:
        queries.append({'text': aspect, 'origin': 'missing_aspect', 'relation': 'same_concept'})
        variants, _, _ = concept_variants(aspect)
        queries += variants[:2]
    if not queries:
        # Nothing explicit was missing: widen with the lexicon's related forms instead.
        _, related, _ = concept_variants(state['user_input'])
        queries = [{**r, 'origin': r['origin']} for r in related[:4]]
    if not queries:
        try:
            result, _ = await get_chat_model('subtopics').invoke(
                SUBTOPIC_RULES,
                json.dumps({'question': state['user_input'], 'missing': missing}, ensure_ascii=False), True)
            queries = [{'text': str(q), 'origin': 'model_subtopic', 'relation': 'same_concept'}
                       for q in (result.get('queries') or [])[:4] if str(q).strip()]
        except Exception as exc:
            diagnostics.record('expansion', failure=type(exc).__name__)
    return queries[:6]


async def run(state):
    started = time.monotonic()
    queries = await subtopic_queries(state)
    if not queries:
        diagnostics.record('expansion', skipped='no subtopic queries available')
        return {'search_rounds': state.get('search_rounds', 0) + 1, 'expanded': True}
    shown = {w['page_start'] for w in (state.get('evidence_windows') or [])}
    try:
        # Stay inside the reader's chapter focus when the first round found material there.
        scope = state.get('scope') if state.get('scope_applied') else None
        candidates, report = await search(queries, scope=scope) if scope else await search(queries)
    except Exception as exc:
        diagnostics.record('expansion', failure=type(exc).__name__)
        return {'search_rounds': state.get('search_rounds', 0) + 1, 'expanded': True}
    merged = list(state.get('retrieved_chunks') or []) + candidates
    # Search the WHOLE pool, first round included. Selecting only from the new candidates
    # replaced the evidence instead of extending it: a question whose answer was on a page
    # found in round one lost that page the moment a second round ran, and the reader was
    # told the book does not answer the question while the supporting page had been found
    # and then discarded. `shown` is no longer excluded for the same reason — it is ranked
    # alongside the new material so the best evidence from both rounds survives.
    concepts = state.get('matched_concepts') or ()
    windows, selection = select(merged, token_budget=token_budget(), max_windows=window_count(),
                                concepts=concepts)
    if not windows:
        windows, selection = select(candidates, token_budget=token_budget(), max_windows=window_count(),
                                    concepts=concepts)
    diagnostics.stage('expand', time.monotonic() - started, queries=[q['text'] for q in queries])
    # `report` carries its own 'queries' (the per-retriever report). Spreading it next to a
    # 'queries' keyword raised TypeError and killed the whole request on every second search
    # round, which the reader saw as a failed answer. Keep the two under distinct names.
    diagnostics.record('expansion',
                       subtopic_queries=[{'text': q['text'], 'origin': q['origin']} for q in queries],
                       first_round_pages=sorted(shown), new_pages=selection.get('selected_pages', []),
                       retriever_report={k: v for k, v in report.items() if k != 'candidate_pages'})
    return {'retrieved_chunks': merged, 'evidence_windows': windows or state.get('evidence_windows') or [],
            'search_rounds': state.get('search_rounds', 0) + 1, 'expanded': True,
            'previous_windows': state.get('evidence_windows') or []}
