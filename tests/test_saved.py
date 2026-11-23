"""Saved answers (loop 2, 2026-11-17): add, de-duplicate, list newest first, open, delete, validate."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import routes_saved
from app.core import saved

ANSWER = {'question': 'Misaq-e-Madina kya tha?', 'answer': '### Misaq\nEk muahida tha [1].',
          'citations': [{'id': 1, 'book_id': '46a52585612a906c', 'book_title': 'Muqaddima', 'page': 383,
                         'excerpt': 'میثاق مدینہ'}], 'verification': 'audited', 'session_id': 'abc'}


def client(tmp_path, monkeypatch):
    monkeypatch.setattr(saved, 'SAVED_DIR', tmp_path)
    monkeypatch.setattr(saved, 'SAVED_FILE', tmp_path / 'saved.json')
    app = FastAPI()
    app.include_router(routes_saved.router)
    return TestClient(app)


def test_save_list_open_delete(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    first = c.post('/saved', json=ANSWER).json()
    assert first['created'] is True
    again = c.post('/saved', json=ANSWER).json()
    assert again == {'id': first['id'], 'created': False}          # no duplicate
    second = c.post('/saved', json={**ANSWER, 'question': 'Hijrat?', 'answer': 'Hijrat [1].'}).json()
    listing = c.get('/saved').json()
    assert [i['id'] for i in listing] == [second['id'], first['id']]  # newest first
    assert listing[1]['pages'] == [383] and 'citations' not in listing[1] and listing[1]['preview']
    full = c.get(f"/saved/{first['id']}").json()
    assert full['citations'][0]['excerpt'] == 'میثاق مدینہ'
    assert c.delete(f"/saved/{first['id']}").json() == {'deleted': True}
    assert c.get(f"/saved/{first['id']}").status_code == 404
    assert len(c.get('/saved').json()) == 1


def test_validation_and_bad_ids(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.post('/saved', json={'question': 'q', 'answer': ''}).status_code == 422
    assert c.post('/saved', json={**ANSWER, 'session_id': '../x'}).status_code == 422
    assert c.get('/saved/../../etc').status_code == 404
    assert c.delete('/saved/notanid').status_code == 404


def test_corrupt_file_reads_as_empty(tmp_path, monkeypatch):
    client(tmp_path, monkeypatch)
    (tmp_path / 'saved.json').write_text('{broken', encoding='utf-8')
    assert saved.listing() == []
