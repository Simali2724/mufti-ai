"""Accuracy guards of 2026-11-18: two-tier audit, citations for uncited sentences, number hints,
un-quoting of non-verbatim quotations. Offline, mocked models."""
import json
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from app.agents import explain_agent
from app.agents.explain_agent import numbers_in, unquote_unverified, citations_for_uncited, sentence_units
from app.agents.graph import build_graph, ask
from app.core.schemas import ChatRequest
from tests.test_explain import FakeModel, install, two_windows, PAGE_257


def test_numbers_in_every_script():
    assert numbers_in('Article 27, ۲۷ and २७ and ٢٧') == {'27'}
    assert numbers_in('no digits') == set()


def test_verbatim_quote_kept_paraphrase_unquoted():
    sources = [{'text': PAGE_257}]
    kept = 'It says “there shall be no gender discrimination in adult franchise” [1].'
    assert unquote_unverified(kept, sources) == (kept, 0)
    invented = 'It says “men and women must always vote together on every single matter” [1].'
    body, count = unquote_unverified(invented, sources)
    assert count == 1 and '“' not in body and 'men and women must always vote' in body
    short = 'It is called “adult franchise” here [1].'                 # under 6 words: left alone
    assert unquote_unverified(short, sources) == (short, 0)


def test_citations_added_only_to_uncited_unflagged_sentences():
    body = 'The Charter bars gender discrimination in adult franchise.\nEvery adult has a vote [1].\nA claim nobody supports here.'
    units = sentence_units(body)
    proposals = [{'id': 1, 'cites': [2, 9]}, {'id': 2, 'cites': [2]}, {'id': 3, 'cites': [1]}]
    problems = [{'id': 3, 'issue': 'unsupported', 'fix': ''}]
    fixes = citations_for_uncited(units, proposals, problems, limit=2)
    assert fixes == [{'id': 1, 'issue': 'citation_added',
                      'fix': 'The Charter bars gender discrimination in adult franchise [2].'}]


class Judge(FakeModel):
    """Answer streams normally; the audit returns a scripted verdict and records what it saw."""
    seen = []

    def __init__(self, text, verdict, fail_strong=False, task='explain'):
        super().__init__(text)
        self.verdict, self.fail_strong, self.task = verdict, fail_strong, task

    async def invoke(self, system, user, structured=False):
        Judge.seen.append((self.task, json.loads(user)))
        if self.task == 'audit_strong' and self.fail_strong:
            raise RuntimeError('strong judge down')
        return self.verdict, 'gemini'


def install_judge(monkeypatch, text, verdict, fail_strong=False):
    Judge.seen = []
    install(monkeypatch, FakeModel(text), two_windows())
    monkeypatch.setattr(explain_agent, 'get_chat_model',
                        lambda task: Judge(text, verdict, fail_strong, task))


@pytest.mark.explain
@pytest.mark.asyncio
async def test_strong_audit_runs_first_and_adds_missing_citation(monkeypatch):
    text = ('<<full>>\nEvery adult man and woman of the community has an equal right to vote.\n'
            'Article 27 bars gender discrimination in adult franchise [2].')
    install_judge(monkeypatch, text, {'problems': [], 'add_citations': [{'id': 1, 'cites': [2]}]})
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='Who could vote?'))
    tasks = [t for t, _ in Judge.seen]
    assert tasks == ['audit_strong']
    assert r.verification == 'audited'
    first_line = r.answer.splitlines()[0]
    assert first_line.endswith('[1].') and 'equal right to vote' in first_line   # citation now attached


@pytest.mark.explain
@pytest.mark.asyncio
async def test_lite_audit_takes_over_when_strong_fails(monkeypatch):
    text = '<<full>>\nArticle 27 bars gender discrimination in adult franchise [2].'
    install_judge(monkeypatch, text, {'problems': [], 'add_citations': []}, fail_strong=True)
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='Who could vote?'))
    assert [t for t, _ in Judge.seen] == ['audit_strong', 'audit'] and r.verification == 'audited'


@pytest.mark.explain
@pytest.mark.asyncio
async def test_number_missing_from_sources_is_flagged_to_the_judge(monkeypatch):
    text = ('<<full>>\nArticle 27 bars gender discrimination in adult franchise [2].\n'
            'The Charter was signed by 1500 people [2].')
    install_judge(monkeypatch, text, {'problems': [], 'add_citations': []})
    await ask(build_graph(InMemorySaver()), ChatRequest(question='Who could vote?'))
    sentences = Judge.seen[0][1]['sentences']
    flags = {s['id']: s.get('numbers_not_in_sources') for s in sentences}
    assert flags[1] is None                      # 27 is in the source
    assert flags[2] == ['1500']                  # invented number is pointed out to the judge


def test_audit_schema_has_no_bounds_in_add_citations():
    """Gemini returned HTTP 400 ("too many states") for the bounded version (live, 2026-11-18)."""
    from app.llm.structured import SCHEMAS
    text = json.dumps(SCHEMAS['audit']['properties']['add_citations'])
    assert 'maxItems' not in text and 'minItems' not in text and 'minimum' not in text
    assert SCHEMAS['audit_strong'] is SCHEMAS['audit']


@pytest.mark.asyncio
async def test_failing_strong_audit_does_not_trip_the_provider(monkeypatch):
    """Live 2026-11-18: the strong audit's 400 tripped Gemini and the next question went local."""
    import httpx
    from app.llm import router
    from app.core.config import settings
    monkeypatch.setattr(settings, 'google_api_key', 'test-key')
    router.breaker.success('gemini')

    async def bad_request(*args, **kwargs):
        raise httpx.HTTPStatusError('400', request=httpx.Request('POST', 'https://x'),
                                    response=httpx.Response(400))
    monkeypatch.setattr(router, 'complete', bad_request)
    for _ in range(4):
        with pytest.raises(router.ProviderUnavailable):
            await router.get_chat_model('audit_strong').invoke('rules', '{}', True)
    assert router.breaker.available('gemini')


@pytest.mark.asyncio
async def test_long_answers_are_judged_in_parallel_chunks(monkeypatch):
    calls = []

    class Strong:
        async def invoke(self, system, user, structured=False):
            ids = [s['id'] for s in json.loads(user)['sentences']]
            calls.append(ids)
            return {'problems': [{'id': ids[0], 'issue': 'unsupported', 'fix': ''}], 'add_citations': []}, 'gemini'
    monkeypatch.setattr(explain_agent, 'get_chat_model', lambda task: Strong())
    payload = {'sources': [], 'question': 'q', 'sentences': [{'id': i, 'text': f's{i}', 'cites': [1]} for i in range(1, 43)]}
    merged, provider = await explain_agent.chunked_audit('audit_strong', payload, 5)
    assert [len(c) for c in calls] == [14, 14, 14]                     # 42 sentences -> 3 even chunks <= 18
    assert sorted(i for c in calls for i in c) == list(range(1, 43))  # every sentence judged exactly once
    assert [p['id'] for p in merged['problems']] == [1, 15, 29] and provider == 'gemini'


@pytest.mark.asyncio
async def test_strong_audit_on_gemini3_uses_low_thinking(monkeypatch):
    """gemini-3-flash-preview timed out with default thinking and answered in 2.3 s with low (2026-11-18)."""
    import httpx
    from app.llm import providers
    from app.core.config import settings
    monkeypatch.setattr(settings, 'google_api_key', 'test-key')
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': '{"problems": []}'}]}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(providers.httpx, 'AsyncClient',
                        lambda **kw: original(transport=httpx.MockTransport(handler)))
    msgs = [{'role': 'system', 'content': 's'}, {'role': 'user', 'content': 'u'}]
    await providers.complete('gemini', 'gemini-3-flash-preview', msgs, True, {'type': 'object'}, 'audit_strong')
    await providers.complete('gemini', 'gemini-2.5-flash', msgs, True, {'type': 'object'}, 'audit_strong')
    await providers.complete('gemini', 'gemini-3-flash-preview', msgs, True, {'type': 'object'}, 'audit')
    assert sent[0]['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'low'}
    assert 'thinkingConfig' not in sent[1]['generationConfig'] and 'thinkingConfig' not in sent[2]['generationConfig']
