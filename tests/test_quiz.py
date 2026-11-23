"""Quiz from an answer (loop 3, 2026-11-17): only cited statements are quizzed, and a question
whose correct option is not supported by the statement it names is dropped."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.agents import quiz_agent
from app.api import routes_quiz

ANSWER = ('<<full>>\nThe Charter of Madinah was a written constitution agreed after the Hijrah [1].\n\n'
          '### Rights\n- It gave every adult man and woman an equal right to vote [2].\n'
          '- Jewish tribes kept the freedom to follow their own religion [1].\n'
          'This is an introduction without a citation and it must not be quizzed.')
CITATIONS = [{'id': 1, 'book_id': 'b', 'book_title': 'Book', 'page': 383},
             {'id': 2, 'book_id': 'b', 'book_title': 'Book', 'page': 257}]
TURN = {'question': 'Misaq-e-Madina kya tha?', 'answer': ANSWER, 'citations': CITATIONS, 'grounded': True,
        'language': 'English'}


def test_only_cited_sentences_become_statements():
    facts = quiz_agent.statements(ANSWER, {1, 2})
    assert [f['cites'] for f in facts] == [[1], [2], [1]]
    assert all('introduction' not in f['text'] for f in facts)


def test_validation_keeps_supported_and_drops_invented():
    facts = quiz_agent.statements(ANSWER, {1, 2})
    raw = {'questions': [
        {'question': 'Who had an equal right to vote?', 'options': ['Only elders', 'Every adult man and woman', 'Nobody'],
         'correct': 1, 'statement': 2, 'explanation': 'Every adult man and woman had an equal right to vote.'},
        {'question': 'In which year was it signed?', 'options': ['622', '630', '610'], 'correct': 0, 'statement': 1,
         'explanation': 'It was signed in 622.'},                       # invented date -> dropped
        {'question': 'Bad statement id', 'options': ['a', 'b', 'c'], 'correct': 0, 'statement': 9, 'explanation': ''},
        {'question': 'Duplicate options', 'options': ['x', 'x', 'y'], 'correct': 0, 'statement': 1, 'explanation': ''},
        {'question': 'Correct out of range', 'options': ['a', 'b', 'c'], 'correct': 5, 'statement': 1, 'explanation': ''},
    ]}
    out = quiz_agent.validate(raw, facts, CITATIONS)
    assert [q['question'] for q in out] == ['Who had an equal right to vote?']
    assert out[0]['sources'] == [{'id': 2, 'book_id': 'b', 'book_title': 'Book', 'page': 257}]


@pytest.mark.asyncio
async def test_make_quiz_uses_one_call_on_the_quiz_task(monkeypatch):
    calls = []

    class Model:
        async def invoke(self, system, user, structured=False):
            calls.append((system, user, structured))
            return {'questions': [{'question': 'What was the Charter of Madinah?',
                                   'options': ['A written constitution agreed after the Hijrah', 'A poem', 'A market'],
                                   'correct': 0, 'statement': 1,
                                   'explanation': 'It was a written constitution agreed after the Hijrah.'}]}, 'gemini'

    monkeypatch.setattr(quiz_agent, 'get_chat_model', lambda task: Model() if task == 'quiz' else None)
    result = await quiz_agent.make_quiz(TURN, 3)
    assert len(calls) == 1 and calls[0][2] is True and 'English' in calls[0][0]
    assert 'equal right to vote' in calls[0][1] and 'introduction' not in calls[0][1]   # statements only
    assert result['questions'][0]['cites'] == [1]


def test_short_answer_is_refused():
    with pytest.raises(ValueError):
        import asyncio
        asyncio.run(quiz_agent.make_quiz({**TURN, 'answer': 'One fact [1].'}))


class FakeState:
    def __init__(self, history):
        self.values = {'history': history}


class FakeGraph:
    def __init__(self, history):
        self.history = history

    async def aget_state(self, config):
        return FakeState(self.history)


def api(history):
    app = FastAPI()
    app.include_router(routes_quiz.router)
    app.state.graph = FakeGraph(history)
    return TestClient(app)


def test_route_refuses_unknown_or_ungrounded_answers():
    c = api([{**TURN, 'grounded': False, 'citations': []}])
    assert c.post('/quiz', json={'session_id': 's1', 'question': 'Other question'}).status_code == 404
    assert c.post('/quiz', json={'session_id': 's1', 'question': TURN['question']}).status_code == 409
    assert c.post('/quiz', json={'session_id': '../x', 'question': 'q'}).status_code == 422
