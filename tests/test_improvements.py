import json
import pytest
from app.retrieval.query_expansion import expand_query
from app.agents import formatter,verifier_agent
from app.llm.preferences import model_request,request_trace

def test_name_alias():
    q,v,concepts=expand_query('Who is Mahomet explain')
    assert q=='Who is Muhammad explain' and any('محمد' in item['text'] for item in v)
    assert all('origin' in item and 'relation' in item for item in v)

def test_lexicon_variants_cover_scripts_without_merging_related_concepts():
    q,variants,concepts=expand_query('Explain Gender Equality in detail')
    assert 'gender_equality' in concepts
    texts={item['text'] for item in variants}
    assert 'صنفی مساوات' in texts and 'عورت اور مرد کی برابری' in texts
    same={item['text'] for item in variants if item['relation']=='same_concept'}
    related={item['text'] for item in variants if item['relation']=='related_concept'}
    assert 'خواتین کے حقوق کا تحفظ' in related and 'خواتین کے حقوق کا تحفظ' not in same

def test_history_preserves_model_and_failure_reason():
    with model_request():
        request_trace.get().append({'task':'router','provider':'ollama','model':'gemma3:1b','fallback':True})
        result=formatter.run({'user_input':'Unknown topic','detected_language':'English','intent':'general','retrieved_chunks':[],'evidence_windows':[],'history':[]})
    turn=result['history'][-1]
    assert turn['model_used']=='gemma3:1b' and turn['reason_code']=='no_matching_passages'
    assert turn['citations']==[] and not turn['grounded']

@pytest.mark.asyncio
async def test_no_answer_triggers_a_second_subtopic_search_before_refusing(monkeypatch):
    # The second round is affordable on a cloud model, so pin one: locally it is skipped on
    # purpose, which test_local_models_report_the_first_round_instead_of_a_second_expensive_one
    # covers separately.
    from app.agents import retriever_agent
    monkeypatch.setattr(retriever_agent,'answering_provider',lambda:'gemini')
    from app.agents.graph import after_verify
    state={'draft_answer':{'coverage':'none','claims':[],'missing_aspects':[]},
           'verification_report':{'passed':False},'search_rounds':1,'retries':1,'errors':[]}
    assert after_verify(state)=='expand'
    assert after_verify({**state,'search_rounds':2})=='format'
    # A service failure must not be retried as if the book lacked evidence.
    assert after_verify({**state,'errors':['Answer unavailable: HTTPStatusError']})=='format'

@pytest.mark.asyncio
async def test_partial_coverage_with_missing_aspects_searches_again(monkeypatch):
    from app.agents import retriever_agent
    monkeypatch.setattr(retriever_agent,'answering_provider',lambda:'gemini')
    from app.agents.graph import after_verify
    state={'draft_answer':{'coverage':'partial','claims':[{'claim_id':1}],'missing_aspects':['inheritance']},
           'verification_report':{'passed':True},'search_rounds':1,'retries':1,'errors':[]}
    assert after_verify(state)=='expand'

@pytest.mark.asyncio
async def test_live_model_status_names_actual_model(monkeypatch):
    from app.llm import router
    from app.llm.progress import progress_sink
    from app.llm.preferences import Preferences
    from app.llm.circuit_breaker import CircuitBreaker
    events=[]
    async def sink(event): events.append(event)
    async def complete(*args): return 'result'
    monkeypatch.setattr(router,'get_preferences',lambda:Preferences(mode='ollama',models={'ollama':'gemma3:1b','openai':'test','anthropic':'test','gemini':'test'}))
    monkeypatch.setattr(router,'complete',complete)
    monkeypatch.setattr(router,'breaker',CircuitBreaker())
    token=progress_sink.set(sink)
    try: await router.get_chat_model('answer').invoke('system','question')
    finally: progress_sink.reset(token)
    assert events[0]['model']=='gemma3:1b' and events[0]['state']=='running'
    assert events[-1]['state']=='complete'


@pytest.mark.asyncio
async def test_long_answer_claims_are_all_verified_in_batches(monkeypatch):
    """A sectioned answer may draft more claims than one verifier call can reference.

    The verifier schema numbers claim ids 1..answer_max_claims. When the answer agent drafted
    more than that, every claim past the limit received no verdict and was dropped as
    unsupported even though its span supported it. Claims must now be verified in batches,
    renumbered inside each batch, so none is lost.
    """
    from app.core.config import settings
    total = settings.answer_max_claims * 2 + 1
    batches = []

    async def fake_invoke(system, user, structured=False):
        payload = json.loads(user)
        ids = [c['claim_id'] for c in payload['claims']]
        batches.append(ids)
        assert len(ids) <= settings.answer_max_claims, 'batch exceeds the verifier id range'
        assert ids == list(range(1, len(ids) + 1)), 'claim ids must be renumbered inside the batch'
        return ({'claims': [{'claim_id': i, 'supported': True, 'attribution_correct': True,
                             'answers_question': True, 'feedback': ''} for i in ids],
                 'language_correct': True}, 'ollama')

    monkeypatch.setattr(verifier_agent, 'get_chat_model',
                        lambda task: type('M', (), {'invoke': staticmethod(fake_invoke)})())
    claims = [{'claim_id': i + 1, 'text': f'Claim {i + 1}.', 'page': 50, 'support': 'span'}
              for i in range(total)]
    verdicts, language_correct, provider = await verifier_agent.model_pass('q', 'English', claims)
    assert len(batches) == 3 and language_correct and provider == 'ollama'
    assert sorted(verdicts) == [c['claim_id'] for c in claims]
    assert all(v['supported'] for v in verdicts.values())


@pytest.mark.asyncio
async def test_expand_round_records_diagnostics_without_crashing(monkeypatch):
    """The second search round used to raise TypeError and kill the whole request.

    `search()` returns a report that itself contains a 'queries' key. Spreading that report
    into diagnostics.record() alongside an explicit queries= keyword gave
    "got multiple values for keyword argument 'queries'", so any question that needed a
    second round failed outright instead of answering.
    """
    from app.agents import expand_agent
    from app.core import diagnostics

    async def fake_search(queries, limit=None):
        return ([{'id': 'c1', 'text': 'A passage about the franchise.', 'page_start': 257,
                  'book_id': 'b', 'book_title': 'T', 'dense_score': .9, 'lexical_score': .9,
                  'rrf': .1, 'matched_queries': []}],
                {'mode': 'segments', 'corpus': 10, 'queries': [{'query': 'x'}],
                 'candidate_pages': [257]})

    monkeypatch.setattr(expand_agent, 'search', fake_search)
    diagnostics.start('q')
    state = {'user_input': 'Explain gender equality in detail', 'search_rounds': 1,
             'evidence_windows': [{'page_start': 50}], 'retrieved_chunks': [],
             'draft_answer': {'missing_aspects': ['voting rights']}}
    result = await expand_agent.run(state)
    assert result['search_rounds'] == 2 and result['expanded'] is True
    recorded = diagnostics.current()['expansion']
    assert [q['text'] for q in recorded['subtopic_queries']] == ['voting rights']
    assert recorded['retriever_report']['queries'] == [{'query': 'x'}]
    assert recorded['first_round_pages'] == [50]


@pytest.mark.asyncio
async def test_expand_round_keeps_the_first_rounds_evidence(monkeypatch):
    """A second search round must extend the evidence, never replace it.

    Selecting only from the newly retrieved candidates meant the page that actually answered
    the question was dropped the moment a second round ran, and the reader was told the book
    does not answer it while that page had been found and then discarded.
    """
    from app.agents import expand_agent
    from app.core import diagnostics

    def chunk(page, text, score):
        return {'id': f'c{page}', 'text': text, 'page_start': page, 'page_end': page,
                'book_id': 'b', 'book_title': 'T', 'parent_id': f'p{page}', 'parent_text': text,
                'dense_score': score, 'lexical_score': score, 'rrf': score / 10,
                'matched_queries': [], 'chapter': ''}

    first_round = chunk(50, 'The fault line involves issues of gender equality. ' * 6, .9)

    async def fake_search(queries, limit=None):
        return ([chunk(257, 'No gender discrimination in adult franchise applies here. ' * 6, .5)],
                {'mode': 'segments', 'corpus': 2, 'queries': [], 'candidate_pages': [257]})

    monkeypatch.setattr(expand_agent, 'search', fake_search)
    diagnostics.start('q')
    result = await expand_agent.run({
        'user_input': 'Explain gender equality in detail', 'search_rounds': 1,
        'evidence_windows': [{'page_start': 50}], 'retrieved_chunks': [first_round],
        'draft_answer': {'missing_aspects': ['voting rights']}})
    pages = {w['page_start'] for w in result['evidence_windows']}
    assert 50 in pages, 'the first round page must survive the expand round'
    assert 257 in pages, 'the new subtopic page must also be present'


def test_a_claim_is_not_discarded_for_a_missing_full_stop():
    """Punctuation is presentation, not evidence; the sentence is closed rather than dropped."""
    from app.agents import verifier_agent as v
    span = 'The social values of gender equality lie at the heart of any clash'
    window = {'source_id': 1, 'text': span, 'spans': [{'span_id': 1, 'text': span}]}
    claim = {'source_id': 1, 'text': 'The book links gender equality to a cultural fault line',
             'support': span}
    draft = {'claims': [{**claim, 'claim_id': 1}]}
    kept, rejected = v.structural_pass(draft, [window], 'English')
    assert rejected == [] and len(kept) == 1
    assert kept[0]['text'].endswith('.')
    # A claim that genuinely trails off in a connector is still rejected.
    trailing = {'claims': [{**claim, 'claim_id': 2, 'text': 'The book links gender equality and'}]}
    kept2, rejected2 = v.structural_pass(trailing, [window], 'English')
    assert kept2 == [] and 'connector' in rejected2[0]['reason']
    # Urdu and Hindi get their own full stop, not a Latin period.
    assert v.terminate('کتاب مساوات کا ذکر کرتی ہے', 'Urdu').endswith('۔')
    assert v.terminate('किताब समानता का उल्लेख करती है', 'Hindi').endswith('।')


def test_local_models_report_the_first_round_instead_of_a_second_expensive_one(monkeypatch):
    """A second search round costs another answer plus verifier call.

    Measured on this 2 GB GPU those are 215-550s each, and a live request that took the
    second round ran past 1800s while the second answer call timed out twice. Locally the
    first round's result is reported; a cloud model still expands.
    """
    from app.agents import graph
    state = {'verification_report': {'passed': False, 'rejected': [{'reason': 'x'}]},
             'draft_answer': {'coverage': 'none'}, 'search_rounds': 1, 'retries': 1}

    monkeypatch.setattr(graph, 'max_search_rounds', lambda: 1)
    assert graph.after_verify(state) == 'format'
    monkeypatch.setattr(graph, 'max_search_rounds', lambda: 2)
    assert graph.after_verify(state) == 'expand'
    # A service failure is never retried as if it were missing evidence.
    assert graph.after_verify({**state, 'verification_report': {'service_failure': True}}) == 'format'


def test_max_search_rounds_follows_the_answering_provider(monkeypatch):
    from app.agents import graph
    from app.agents import retriever_agent
    monkeypatch.setattr(graph.settings, 'max_search_rounds_local', 1)
    monkeypatch.setattr(retriever_agent, 'answering_provider', lambda: 'ollama')
    assert graph.max_search_rounds() == 1
    monkeypatch.setattr(retriever_agent, 'answering_provider', lambda: 'gemini')
    assert graph.max_search_rounds() == graph.MAX_SEARCH_ROUNDS
