"""Agent/GenAI upgrade of 2026-11-17: answer styles, follow-up questions, chapter scope,
outline/suggestion endpoints and the setup check. Offline, with mocked models."""
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError
from app.agents import suggest, explain_agent, formatter
from app.agents.graph import build_graph, ask
from app.core.schemas import ChatRequest
from tests.test_explain import FakeModel, install, two_windows


# ------------------------------------------------------------------ follow-up parsing
def test_followup_marker_is_split_off_and_cleaned():
    body, questions = suggest.split_followups(
        '<<full>>\nAnswer [1].\n<<next: What was it? | Who wrote [2] it? | x | What was it?>>')
    assert body == '<<full>>\nAnswer [1].'
    assert questions == ['What was it?', 'Who wrote it?']        # citation, too-short, duplicate removed


def test_unterminated_followup_marker_is_still_removed():
    body, questions = suggest.split_followups('Answer [1].\n<<next: One more question here')
    assert body == 'Answer [1].' and questions == ['One more question here']


def test_no_marker_leaves_text_untouched():
    assert suggest.split_followups('Answer [1].') == ('Answer [1].', [])


def test_topic_title_strips_chapter_prefix():
    assert suggest.topic_title('Chapter Four: Biological Stages') == 'Biological Stages'
    assert suggest.topic_title('باب 4: سیرت الرسول') == 'سیرت الرسول'


def test_outline_followups_skip_contents_and_duplicates(monkeypatch):
    from app.ingestion import book_tree
    places = {1: {'chapter': 'Contents', 'section': ''}, 2: {'chapter': 'Chapter One: Bones', 'section': 'Bone growth'},
              3: {'chapter': 'Chapter One: Bones', 'section': 'Bone growth'}}
    monkeypatch.setattr(book_tree, 'locate', lambda book, page: places.get(page, {}))
    out = suggest.from_outline([{'book_id': 'b', 'page': p} for p in (1, 2, 3)], 'English')
    # Contents page skipped; one suggestion per distinct section/chapter, never repeated.
    assert out == ['Explain “Bone growth” in detail', 'Explain “Bones” in detail']


# ------------------------------------------------------------------ styles and prompt notes
def state(style='detailed', **extra):
    return {'user_input': 'Explain the Charter', 'detected_language': 'English', 'history': [],
            'answer_style': style, **extra}


def test_style_note_is_added_only_for_non_default_styles(monkeypatch):
    monkeypatch.setattr(explain_agent, 'wants_model_followups', lambda: False)
    sources = explain_agent.build_sources(two_windows())
    assert 'STYLE' not in explain_agent.user_message(state('detailed'), sources)
    for style in ('short', 'simple', 'points'):
        message = explain_agent.user_message(state(style), sources)
        assert explain_agent.STYLE_NOTES[style] in message
        assert 'citation' in explain_agent.STYLE_NOTES[style]        # no style relaxes citations


def test_followup_request_only_for_cloud_models(monkeypatch):
    sources = explain_agent.build_sources(two_windows())
    monkeypatch.setattr(explain_agent, 'wants_model_followups', lambda: True)
    assert '<<next:' in explain_agent.user_message(state(), sources)
    monkeypatch.setattr(explain_agent, 'wants_model_followups', lambda: False)
    assert '<<next:' not in explain_agent.user_message(state(), sources)


def test_scope_note_only_when_scope_was_applied():
    scope = {'book_id': 'b', 'page_start': 10, 'page_end': 17, 'label': 'Chapter One'}
    assert explain_agent.scope_note(state(scope=scope, scope_applied=False)) == ''
    assert 'Chapter One' in explain_agent.scope_note(state(scope=scope, scope_applied=True))


def test_request_validation():
    assert ChatRequest(question='q').answer_style == 'detailed'
    with pytest.raises(ValidationError):
        ChatRequest(question='q', answer_style='poem')
    with pytest.raises(ValidationError):
        ChatRequest(question='q', scope={'book_id': '../etc'})
    assert ChatRequest(question='q', scope={'book_id': 'abc', 'page_start': 3}).scope.page_start == 3


# ------------------------------------------------------------------ end to end
@pytest.mark.explain
@pytest.mark.asyncio
async def test_followups_reach_the_response_and_never_the_answer(monkeypatch):
    text = ('<<full>>\nThe Charter bars gender discrimination in adult franchise [2].\n'
            '<<next: Who could vote under the Charter? | What did Inglehart and Norris argue?>>')
    install(monkeypatch, FakeModel(text, audit={'problems': []}), two_windows())
    monkeypatch.setattr(explain_agent, 'wants_model_followups', lambda: True)
    r = await ask(build_graph(InMemorySaver()), ChatRequest(question='Explain the Charter', answer_style='short'))
    assert r.grounded and '<<' not in r.answer and 'next' not in r.answer
    assert r.followups[:2] == ['Who could vote under the Charter?', 'What did Inglehart and Norris argue?']
    assert r.answer_style == 'short'


@pytest.mark.explain
@pytest.mark.asyncio
async def test_scope_is_reported_with_applied_flag(monkeypatch):
    text = '<<full>>\nThe Charter bars gender discrimination in adult franchise [2].'
    install(monkeypatch, FakeModel(text, audit={'problems': []}), two_windows())
    r = await ask(build_graph(InMemorySaver()),
                  ChatRequest(question='Explain the Charter', scope={'book_id': 'b', 'page_start': 250,
                                                                     'page_end': 260, 'label': 'Charter'}))
    assert r.scope['book_id'] == 'b' and r.scope['applied'] is False    # the mocked retriever sets none


def test_needs_topic_suggests_chapters(monkeypatch):
    monkeypatch.setattr(suggest, 'starter_topics', lambda language, limit=3: ['Explain “Bones” in detail'])
    out = formatter.next_questions({'intent': 'needs_topic'}, 'needs_topic', False, [], [], 'English')
    assert out == ['Explain “Bones” in detail']


def test_service_failure_gets_no_suggestions():
    assert formatter.next_questions({}, 'provider_unavailable', False, [], [], 'English') == []


# ------------------------------------------------------------------ scoped retrieval
def test_scope_predicate():
    from app.retrieval.hybrid import in_scope
    keep = in_scope({'book_id': 'b', 'page_start': 10, 'page_end': 12})
    assert keep({'book_id': 'b', 'page_start': 11}) and not keep({'book_id': 'b', 'page_start': 13})
    assert not keep({'book_id': 'other', 'page_start': 11})
    assert in_scope(None) is None


def test_bm25_keep_filters_without_new_index():
    from app.retrieval import bm25
    chunks = [{'id': 'a', 'text': 'charter of madinah', 'page_start': 1},
              {'id': 'b', 'text': 'charter rights madinah', 'page_start': 9}]
    chunks += [{'id': f'z{i}', 'text': f'unrelated filler words {i}', 'page_start': 20 + i} for i in range(8)]
    hits = bm25.search(chunks, 'charter madinah', 5, keep=lambda c: c['page_start'] > 5)
    assert [h['id'] for h in hits] == ['b']


@pytest.mark.asyncio
async def test_scoped_search_filters_dense_and_sweeps_small_scope(monkeypatch):
    from app.retrieval import hybrid as h
    chunks = [{'id': f's{p}', 'text': f'page {p} text about bones', 'page_start': p, 'book_id': 'b'} for p in range(1, 30)]
    async def embedding(queries): return [[1., 0.] for _ in queries]
    monkeypatch.setattr(h.segment_index, 'load_segments', lambda: chunks)
    monkeypatch.setattr(h, 'embed', embedding)
    monkeypatch.setattr(h.segment_index, 'search_segments', lambda v, k: [{**c, 'dense_score': .8} for c in chunks[:k]])
    monkeypatch.setattr(h.settings, 'enable_knowledge_graph', False)
    candidates, _ = await h.search_local([{'text': 'bones', 'origin': 'original', 'relation': 'same_concept'}],
                                         scope={'book_id': 'b', 'page_start': 20, 'page_end': 24})
    assert candidates and all(20 <= c['page_start'] <= 24 for c in candidates)
    assert any(c.get('scope_hits') for c in candidates)


@pytest.mark.asyncio
async def test_retriever_falls_back_to_library_when_scope_is_empty(monkeypatch):
    from app.agents import retriever_agent
    calls = []
    async def fake_search(queries, limit=None, scope=None):
        calls.append(scope)
        return ([] if scope else [{'id': 'x', 'page_start': 5, 'book_id': 'b', 'text': 'Charter text here.',
                                   'rrf': .1, 'dense_score': .9, 'lexical_score': .5, 'matched_queries': []}]), {}
    monkeypatch.setattr(retriever_agent, 'search', fake_search)
    from tests.test_graph_e2e import window
    monkeypatch.setattr(retriever_agent, 'select', lambda c, **k: ([window('Charter text here.', page=5)] if c else [], {}))
    out = await retriever_agent.run({'user_input': 'q', 'scope': {'book_id': 'b', 'page_start': 1, 'page_end': 2}})
    assert calls == [{'book_id': 'b', 'page_start': 1, 'page_end': 2}, None]
    assert out['scope_applied'] is False and out['evidence_windows']


# ------------------------------------------------------------------ setup check
@pytest.mark.asyncio
async def test_setup_check_reports_offline_ollama_with_fix(monkeypatch):
    from app.core import setup_check
    async def offline(): return False, []
    monkeypatch.setattr(setup_check, 'ollama_models', offline)
    report = await setup_check.run_checks()
    ollama = next(c for c in report['checks'] if c['id'] == 'ollama')
    assert report['status'] == 'fail' and ollama['status'] == 'fail'
    assert 'ollama serve' in ollama['fix'] and ollama['fix_hinglish']
    assert all(set(c) >= {'id', 'label', 'status', 'detail', 'fix', 'fix_hinglish'} for c in report['checks'])


@pytest.mark.asyncio
async def test_setup_check_never_reveals_key_values(monkeypatch):
    from app.core import setup_check
    from app.core.config import settings
    monkeypatch.setattr(settings, 'google_api_key', 'SECRET-KEY-VALUE')
    async def online(): return True, ['bge-m3:latest', 'qwen3:1.7b']
    monkeypatch.setattr(setup_check, 'ollama_models', online)
    report = await setup_check.run_checks()
    assert 'SECRET-KEY-VALUE' not in str(report)


# ------------------------------------------------------------------ topic index (loop 5, 2026-11-18)
def test_topic_index_lists_reviewed_concepts_and_real_sections(monkeypatch):
    from app.ingestion import book_tree
    import app.ingestion.indexer as indexer
    tree = {'chapters': [
        {'id': 'c1', 'title': 'Contents', 'page_start': 1, 'page_end': 4, 'sections': []},
        {'id': 'c2', 'title': 'Chapter Two: Bones', 'page_start': 5, 'page_end': 20,
         'sections': [{'id': 's1', 'title': 'Growth of bones', 'page_start': 6, 'page_end': 9}]}]}
    monkeypatch.setattr(book_tree, 'load', lambda book_id: tree)
    monkeypatch.setattr(indexer, 'catalog', lambda: [{'id': 'b', 'title': 'creation man 1', 'filename': 'x.pdf'}])
    out = suggest.topic_index()
    assert any(c['id'] == 'gender_equality' and 'Urdu' in c['forms'] for c in out['concepts'])
    assert [(s['topic'], s['kind'], s['chapter'], s['page_start']) for s in out['sections']] == [
        ('Bones', 'chapter', '', 5), ('Growth of bones', 'section', 'Bones', 6)]      # contents skipped
