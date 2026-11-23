import time
from contextlib import asynccontextmanager
from langgraph.graph import StateGraph, START, END
from app.core import diagnostics
from app.core.storage import LocalSqliteSaver, ScopedSqliteSaver
from app.core.config import settings, INDEX
from app.core.schemas import ChatResponse
from app.llm.preferences import model_request
from app.agents.state import AgentState
from app.agents import (bibliography, language_agent, router_agent, retriever_agent, answer_agent,
                        verifier_agent, expand_agent, repair_agent, formatter, explain_agent)

MAX_SEARCH_ROUNDS = 2


def max_search_rounds():
    """How many search rounds this request can afford on the model that will answer it.

    A second round costs another answer plus verifier call. Measured on this 2 GB MX450 those
    are 215-550s each, and a live request that took the second round ran past 1800s and the
    client gave up while the second answer call timed out twice. A 30-minute request is worse
    for the reader than a scoped "no direct answer, here are the related pages", so locally the
    first round's result is reported instead. A cloud model pays seconds and still expands.
    """
    from app.agents.retriever_agent import answering_provider
    if answering_provider() != 'ollama':
        return MAX_SEARCH_ROUNDS
    return max(1, settings.max_search_rounds_local)


def after_verify(state):
    """Repair the specific claims that failed, then widen the search, then report.

    Order matters and it is the order the brief gives: a rejected claim is repaired from its
    OWN evidence before anything is abandoned, and only a question whose evidence genuinely
    did not cover it goes back to the index for a second search. The measured failure on this
    book was a single missing attribution on an otherwise correct claim drawn from the right
    page - re-searching the book for that is both slow and pointless.
    """
    report = state.get('verification_report', {})
    if report.get('service_failure') or state.get('errors'):
        return 'format'
    repairable = {r.get('code') for r in report.get('rejected', [])} & verifier_agent.REPAIRABLE_CODES
    if repairable and state.get('repair_rounds', 0) < settings.max_repair_rounds:
        return 'repair'
    coverage = state.get('draft_answer', {}).get('coverage', 'none')
    unresolved = not report.get('passed') or (coverage == 'partial' and state.get('draft_answer', {}).get('missing_aspects'))
    if unresolved and state.get('search_rounds', 1) < max_search_rounds() and state.get('retries', 0) <= settings.max_verifier_retries:
        return 'expand'
    return 'format'


def explain_mode():
    return settings.answer_mode != 'strict'


def after_explain(state):
    """Search once more before saying the book does not answer the question.

    Unlike the strict pipeline this also applies locally: a "<<none>>" reply costs a handful of
    output tokens, so the first round was cheap, and a refusal of an answerable question is
    the failure the reader complained about.
    """
    status = (state.get('explanation') or {}).get('status')
    if (status == 'none' and not state.get('errors') and not state.get('expanded')
            and state.get('search_rounds', 1) < MAX_SEARCH_ROUNDS):
        return 'expand'
    return 'format'


def answer_step(state):
    if not state.get('evidence_windows'):
        return 'format'
    return 'explain' if explain_mode() else 'answer'


def keep_best(state):
    """Prefer the round that actually verified claims; never lose a good first answer."""
    return state


def build_graph(checkpointer):
    graph = StateGraph(AgentState)

    async def input_node(s):
        return {'input_modality': s.get('input_modality', 'text')}

    nodes = [('bibliography', bibliography.run), ('input', input_node), ('language', language_agent.run),
             ('router', router_agent.run), ('retrieve', retriever_agent.run), ('answer', answer_agent.run),
             ('verify', verifier_agent.run), ('repair', repair_agent.run),
             ('expand', expand_agent.run), ('explain', explain_agent.run), ('format', formatter.run)]
    for name, func in nodes:
        graph.add_node(name, func)
    graph.add_edge(START, 'input')
    graph.add_edge('input', 'bibliography')
    graph.add_conditional_edges('bibliography', lambda s: END if s.get('bibliography_answered') else 'language')
    graph.add_edge('language', 'router')
    graph.add_conditional_edges('router',
                                lambda s: 'format' if s['intent'] in ('smalltalk', 'unsafe', 'out_of_scope',
                                                      'needs_topic')
                                else 'retrieve')
    graph.add_conditional_edges('retrieve', answer_step)
    graph.add_conditional_edges('explain', after_explain)
    graph.add_edge('answer', 'verify')
    graph.add_conditional_edges('verify', after_verify)
    # A repair round re-verifies only the rewritten claims; the ones already verified are
    # carried through untouched by verifier_agent, so nothing that worked is lost or re-paid for.
    graph.add_conditional_edges('repair', lambda s: 'verify' if s.get('repaired') else after_verify(s))
    graph.add_conditional_edges('expand', answer_step)
    graph.add_edge('format', END)
    return graph.compile(checkpointer=checkpointer)


@asynccontextmanager
async def graph_context():
    async with LocalSqliteSaver.from_conn_string(str(INDEX / 'sessions.sqlite')) as saver:
        await saver.setup()
    yield build_graph(ScopedSqliteSaver(INDEX / 'sessions.sqlite'))


class PersistentGraph:
    def __init__(self):
        self.checkpointer = self

    async def ainvoke(self, data, config):
        async with graph_context() as graph:
            return await graph.ainvoke(data, config=config)

    async def aget_state(self, config):
        async with graph_context() as graph:
            return await graph.aget_state(config)

    async def adelete_thread(self, thread_id):
        async with graph_context() as graph:
            await graph.checkpointer.adelete_thread(thread_id)


async def ask(graph, request, modality='text', progress=None):
    from app.llm.progress import progress_sink
    token = progress_sink.set(progress)
    diagnostics.start(request.question, request.language_hint)
    try:
        return await _ask(graph, request, modality)
    finally:
        progress_sink.reset(token)


async def _ask(graph, request, modality='text'):
    start = time.monotonic()
    from app.core.resources import interactive_work
    # Per-turn reader choices. Always written into the input, so a value from an earlier turn
    # can never leak through the checkpoint into this one (the 2026-11-16 answer_format bug).
    style = getattr(request, 'answer_style', None) or 'detailed'
    scope = getattr(request, 'scope', None)
    scope = scope.model_dump() if hasattr(scope, 'model_dump') else (scope or {})
    with model_request() as trace:
        async with interactive_work():
            result = await graph.ainvoke(
                {'user_input': request.question, 'language_hint': request.language_hint,
                 'input_modality': modality, 'retries': 0, 'evidence_batch': 0, 'search_rounds': 0, 'repair_rounds': 0,
                 'bibliography_answered': False, 'errors': [], 'explanation': {}, 'explain_rounds': 0,
                 'answer_format': 'text', 'verification': '',
                 'answer_style': style, 'scope': scope, 'scope_applied': False, 'followups': [],
                 'expanded': False, 'retrieved_chunks': [], 'reranked_chunks': [],
                 'evidence_windows': [], 'draft_answer': {}, 'verification_report': {}, 'final_answer': '',
                 'citations': [], 'related': [], 'coverage': 'none', 'provider_used': 'none', 'grounded': False},
                config={'configurable': {'thread_id': request.session_id}})
    event = next((item for item in reversed(trace) if item['task'] in ('answer', 'explain')), trace[-1] if trace else {})
    selected = _selected_route()
    response = ChatResponse(
        answer=result['final_answer'], language=result['detected_language'], citations=result['citations'],
        related=result.get('related', []), provider_used=result['provider_used'],
        model_used=event.get('model', ''), execution=trace, reason_code=result.get('reason_code', ''),
        retrieved_count=len(result.get('retrieved_chunks', [])), fallback_used=event.get('fallback', False),
        grounded=result['grounded'], coverage=result.get('coverage', 'none'),
        missing_aspects=result.get('missing_aspects', []),
        evidence_pages=[w['page_start'] for w in result.get('evidence_windows', [])],
        selected_provider=selected['provider'], selected_model=selected['model'],
        answering_provider=event.get('provider', ''), answering_model=event.get('model', ''),
        fallback_reason=_fallback_reason(trace),
        answer_format=result.get('answer_format', 'text'), verification=result.get('verification', ''),
        followups=result.get('followups') or [], answer_style=style,
        scope={**scope, 'applied': bool(result.get('scope_applied'))} if scope else None,
        latency_ms=round((time.monotonic() - start) * 1000),
        status='limited' if result.get('errors') else 'complete')
    diagnostics.save({'reason_code': response.reason_code, 'grounded': response.grounded,
                      'coverage': response.coverage, 'latency_ms': response.latency_ms,
                      'answering_model': response.answering_model,
                      'selected_model': f"{selected['provider']}/{selected['model']}"})
    return response


def _selected_route():
    from app.llm.preferences import request_preferences, get_preferences, build_provider_order
    preferences = request_preferences.get() or get_preferences()
    provider = build_provider_order(preferences)[0]
    return {'provider': provider, 'model': preferences.models.get(provider, '')}


def _fallback_reason(trace):
    """Why the answering model is not the selected one, in the user's terms."""
    failures = diagnostics.provider_failures()
    if not failures:
        return ''
    parts = []
    for provider, details in failures.items():
        detail = details[-1]
        if '429' in detail:
            parts.append(f'{provider}: quota or rate limit reached')
        elif 'key missing' in detail:
            parts.append(f'{provider}: no API key configured')
        elif 'temporarily unavailable' in detail:
            parts.append(f'{provider}: skipped after repeated failures')
        else:
            parts.append(f'{provider}: {detail}')
    return '; '.join(dict.fromkeys(parts))[:300]
