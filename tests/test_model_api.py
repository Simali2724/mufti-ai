"""Exercise model settings over HTTP without starting the graph or Ollama."""

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_models
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.preferences import Preferences
from app.llm.router import note_outcome


@pytest.fixture
def model_api(monkeypatch):
    prefs = Preferences(models={
        "anthropic": "test-claude",
        "openai": "test-gpt",
        "gemini": "test-gemini",
        "ollama": "gemma3:1b",
    })
    monkeypatch.setattr(routes_models, "get_preferences", lambda: prefs)
    monkeypatch.setattr(routes_models.settings, "embedding_model", "bge-m3")
    monkeypatch.setattr(routes_models.settings, "anthropic_api_key", "")
    monkeypatch.setattr(routes_models.settings, "openai_api_key", "secret-openai-test-value")
    monkeypatch.setattr(routes_models.settings, "google_api_key", "  ")
    monkeypatch.setattr(routes_models, "breaker", CircuitBreaker())
    show_calls = []
    saved = []

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    class OllamaClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def get(self, url):
            assert url.endswith("/api/tags")
            return Response({"models": [
                {"name": "bge-m3:latest"},
                {"name": "nomic-embed-text:latest"},
                {"name": "custom-vector:latest"},
                {"name": "gemma3:1b", "capabilities": ["completion", "vision"]},
                {"name": "qwen3:1.7b"},
                {"name": "unavailable:latest"},
            ]})

        async def post(self, url, json):
            assert url.endswith("/api/show")
            name = json["model"]
            show_calls.append(name)
            if name == "unavailable:latest":
                raise httpx.ConnectError("model details unavailable")
            return Response({"capabilities": ["embedding"] if name == "custom-vector:latest" else ["completion"]})

    def save(selected):
        saved.append(selected)
        return selected

    monkeypatch.setattr(routes_models.httpx, "AsyncClient", OllamaClient)
    monkeypatch.setattr(routes_models, "save_preferences", save)
    application = FastAPI()
    application.include_router(routes_models.router)
    with TestClient(application) as client:
        yield client, prefs, show_calls, saved


def test_get_lists_chat_models_and_excludes_embedding_models(model_api):
    client, _, show_calls, _ = model_api
    response = client.get("/settings/models")
    assert response.status_code == 200
    body = response.json()
    assert body["local_online"] is True
    assert body["installed_ollama_models"] == ["gemma3:1b", "qwen3:1.7b"]
    assert set(show_calls) == {"qwen3:1.7b", "custom-vector:latest", "unavailable:latest"}


def test_get_exposes_key_presence_without_secret_values(model_api):
    client, _, _, _ = model_api
    response = client.get("/settings/models")
    body = response.json()
    assert body["configured"] == {"anthropic": False, "openai": True, "gemini": False}
    assert set(body) == {"mode", "cloud_order", "models", "configured", "provider_state",
                         "installed_ollama_models", "local_online"}
    assert "secret-openai-test-value" not in response.text
    assert "api_key" not in response.text


def test_provider_state_does_not_call_a_configured_key_ready(model_api):
    """A key present in .env is not evidence that the provider answers."""
    client, _, _, _ = model_api
    note_outcome("openai", "")
    state = client.get("/settings/models").json()["provider_state"]
    assert state["gemini"] == {"configured": False, "available": False, "label": "No API key",
                               "detail": "Add a key to .env and restart to use this provider."}
    assert state["openai"]["configured"] is True
    assert state["openai"]["label"] == "Key configured · not yet used"
    assert state["ollama"]["label"] == "Ollama running"
    assert state["ollama"]["available"] is True


def test_provider_state_reports_quota_and_cooldown_instead_of_ready(model_api):
    client, _, _, _ = model_api
    try:
        note_outcome("openai", "HTTP 429 quota exceeded")
        quota = client.get("/settings/models").json()["provider_state"]["openai"]
        assert quota["available"] is False
        assert quota["label"] == "Quota or rate limit reached"
        routes_models.breaker.trip("openai")
        paused = client.get("/settings/models").json()["provider_state"]["openai"]
        assert paused["available"] is False
        assert paused["label"] == "Paused after failures"
    finally:
        note_outcome("openai", "")
        routes_models.breaker.states.clear()


def test_put_saves_valid_selection_and_resets_provider_cooldown(model_api):
    client, prefs, _, saved = model_api
    routes_models.breaker.trip("openai")
    selection = prefs.model_dump()
    selection["mode"] = "ollama"
    selection["models"]["ollama"] = "qwen3:1.7b"
    response = client.put("/settings/models", json=selection)
    assert response.status_code == 200
    assert response.json()["mode"] == "ollama"
    assert response.json()["models"]["ollama"] == "qwen3:1.7b"
    assert [item.model_dump() for item in saved] == [selection]
    assert routes_models.breaker.available("openai")


@pytest.mark.parametrize("field", ["openai_api_key", "api_keys", "unknown"])
def test_put_rejects_unknown_and_secret_fields_without_saving(model_api, field):
    client, prefs, _, saved = model_api
    payload = prefs.model_dump()
    payload[field] = "not-accepted"
    response = client.put("/settings/models", json=payload)
    assert response.status_code == 422
    assert saved == []


@pytest.mark.parametrize("order", [
    ["anthropic", "anthropic", "gemini"],
    ["anthropic", "openai"],
    ["anthropic", "openai", "ollama"],
])
def test_put_rejects_malformed_priority_without_saving(model_api, order):
    client, prefs, _, saved = model_api
    payload = prefs.model_dump()
    payload["cloud_order"] = order
    response = client.put("/settings/models", json=payload)
    assert response.status_code == 422
    assert saved == []
