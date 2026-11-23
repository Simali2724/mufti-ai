"""Voice input, 2026-11-17: POST /transcribe returns text only — it never asks or answers.

The UI puts the transcript into the question box so the reader can check it and press Send.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import routes_voice


def client_with(monkeypatch, result=('Misaq-e-Madina kya tha', 'hi'), seen=None):
    def fake_transcribe(path, language_hint=None):
        if seen is not None:
            seen.append(language_hint)
        return result

    async def must_not_answer(*args, **kwargs):
        raise AssertionError('/transcribe must not run the answer pipeline')

    monkeypatch.setattr(routes_voice, 'transcribe', fake_transcribe)
    monkeypatch.setattr(routes_voice, 'ask', must_not_answer)
    app = FastAPI()
    app.include_router(routes_voice.router)
    return TestClient(app)


def test_transcribe_returns_text_only(monkeypatch):
    seen = []
    client = client_with(monkeypatch, seen=seen)
    r = client.post('/transcribe', files={'audio': ('r.webm', b'fake-audio', 'audio/webm')},
                    data={'language_hint': 'Urdu'})
    assert r.status_code == 200
    assert r.json() == {'transcript': 'Misaq-e-Madina kya tha', 'detected_language': 'hi'}
    assert seen == ['Urdu']


def test_unknown_language_hint_is_not_forwarded(monkeypatch):
    seen = []
    client = client_with(monkeypatch, seen=seen)
    client.post('/transcribe', files={'audio': ('r.webm', b'x', 'audio/webm')}, data={'language_hint': 'Klingon'})
    assert seen == [None]


def test_empty_audio_is_rejected(monkeypatch):
    client = client_with(monkeypatch)
    r = client.post('/transcribe', files={'audio': ('r.webm', b'', 'audio/webm')})
    assert r.status_code == 422


def test_whisper_language_map_leaves_hinglish_to_detection():
    from app.voice.stt import WHISPER_LANGUAGE
    assert WHISPER_LANGUAGE == {'Urdu': 'ur', 'Hindi': 'hi', 'English': 'en'}
