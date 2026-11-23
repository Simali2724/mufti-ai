"""Hybrid retrieval, then selection of coherent evidence windows."""
import time
from app.core import diagnostics
from app.core.config import settings
from app.core.logging import logger
from app.retrieval.hybrid import search
from app.retrieval.evidence import select
from app.llm.preferences import request_preferences, get_preferences, build_provider_order
from app.llm.router import has_key


def answering_provider():
    preferences = request_preferences.get() or get_preferences()
    return next((p for p in build_provider_order(preferences) if has_key(p)), 'ollama')


def token_budget():
    """Fit the evidence to whichever model is actually expected to answer."""
    local = answering_provider() == 'ollama'
    return settings.evidence_token_budget if local else settings.evidence_token_budget_cloud


def window_count():
    """Fewer, bigger windows locally: measured faster AND more claims than a wider set."""
    local = answering_provider() == 'ollama'
    return settings.evidence_windows if local else settings.evidence_windows_cloud


SCOPE_MIN_CANDIDATES = 2


async def run(state):
    queries =state.get('search_queries') or [{'text': state['user_input'], 'origin': 'original',
                                               'relation': 'same_concept'}]
    started = time.monotonic()
    scope, scope_applied = state.get('scope') or None, False
    try:
        if scope:
            # Chapter focus from the UI. Too little inside the scope means the reader asked
            # about something that chapter does not discuss: search the whole library rather
            # than refuse, and report applied=False so the UI can say so honestly.
            candidates, report = await search(queries, scope=scope)
            scope_applied = len(candidates) >= SCOPE_MIN_CANDIDATES
            if not scope_applied:
                candidates, report = await search(queries)
        else:
            candidates, report = await search(queries)
    except Exception as exc:
        logger.exception('Retrieval failed')
        diagnostics.record('retrieval', failure=type(exc).__name__)
        return {'retrieved_chunks': [], 'evidence_windows': [], 'retrieval_failed': True,
                'errors': state.get('errors', []) + ['Retrieval unavailable: ' + type(exc).__name__]}
    windows, selection = select(candidates, token_budget=token_budget(), max_windows=window_count(),
                                concepts=state.get('matched_concepts') or ())
    diagnostics.stage('retrieve', time.monotonic() - started, candidates=len(candidates),
                      scope=scope or {}, scope_applied=scope_applied)
    diagnostics.record('retrieval', round=state.get('search_rounds', 0) + 1, **report,
                       candidate_scores=[{'page': c['page_start'], 'relevance': round(c.get('rrf', 0), 4),
                                          'dense': round(c.get('dense_score', 0), 3),
                                          'lexical': round(c.get('lexical_score', 0), 3),
                                          'relation': c.get('relation')} for c in candidates[:40]])
    diagnostics.record('evidence', **selection,
                       windows=[{'source_id': w['source_id'], 'page': w['page_start'],
                                 'printed_label': w['printed_label'], 'relation': w['relation'],
                                 'relevance': w['relevance'], 'tokens': w['tokens'],
                                 'origins': sorted({m['query'] for m in w['matched_queries']})} for w in windows])
    return {'retrieved_chunks': candidates, 'evidence_windows': windows, 'retrieval_failed': False,
            'search_rounds': state.get('search_rounds', 0) + 1, 'scope_applied': scope_applied}
