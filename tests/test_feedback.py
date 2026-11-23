"""Reader feedback (loop 1, 2026-11-17): stored locally, validated, summarised, and turned into
UNREVIEWED draft benchmark cases only."""
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import routes_feedback
from app.core import feedback


def client(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, 'FEEDBACK_DIR', tmp_path)
    monkeypatch.setattr(feedback, 'FEEDBACK_FILE', tmp_path / 'feedback.jsonl')
    app = FastAPI()
    app.include_router(routes_feedback.router)
    return TestClient(app)


def test_feedback_is_saved_and_summarised(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.post('/feedback', json={'rating': 'up', 'question': 'Misaq-e-Madina kya tha?'}).json()['saved']
    r = c.post('/feedback', json={'rating': 'down', 'question': 'Hijrat kab hui?', 'answer': 'x' * 5000,
                                  'reasons': ['not_found_but_in_book'], 'note': 'page 120', 'pages': [120]})
    assert r.status_code == 200
    rows = [json.loads(l) for l in (tmp_path / 'feedback.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 2 and len(rows[1]['answer']) == 1500          # answer trimmed
    s = c.get('/feedback/summary').json()
    assert s['total'] == 2 and s['up'] == 1 and s['down'] == 1
    assert s['down_by_reason'] == {'not_found_but_in_book': 1}
    assert s['recent_down'][0]['question'] == 'Hijrat kab hui?'


def test_invalid_feedback_is_rejected(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.post('/feedback', json={'rating': 'meh', 'question': 'q'}).status_code == 422
    assert c.post('/feedback', json={'rating': 'down', 'question': 'q', 'reasons': ['hack']}).status_code == 422
    assert c.post('/feedback', json={'rating': 'up', 'question': ''}).status_code == 422
    assert c.post('/feedback', json={'rating': 'up', 'question': 'q', 'session_id': '../x'}).status_code == 422


def test_torn_line_does_not_break_summary(tmp_path, monkeypatch):
    client(tmp_path, monkeypatch)
    (tmp_path / 'feedback.jsonl').write_text('{"rating": "down", "question": "a"}\n{"rating": "do', encoding='utf-8')
    assert feedback.summary()['down'] == 1


def test_drafts_are_unreviewed_and_skip_known_questions(tmp_path, monkeypatch):
    client(tmp_path, monkeypatch)
    lines = [{'id': 'a1', 'rating': 'down', 'question': 'Known question', 'reasons': ['wrong']},
             {'id': 'b2', 'rating': 'down', 'question': 'New question', 'reasons': ['incomplete'], 'pages': [7]},
             {'id': 'c3', 'rating': 'up', 'question': 'Liked question'}]
    (tmp_path / 'feedback.jsonl').write_text(''.join(json.dumps(l) + '\n' for l in lines), encoding='utf-8')
    from eval.feedback_to_cases import drafts
    out = drafts(['known question'])
    assert [d['question'] for d in out] == ['New question']
    assert out[0]['reviewed'] is False and out[0]['expected_pages'] == []
    assert out[0]['cited_pages_at_feedback'] == [7] and out[0]['expectation'].startswith('TODO')
