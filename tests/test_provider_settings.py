"""Provider preferences and fallback behavior; every provider call is mocked."""

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from app.llm import router
from app.llm import preferences as preferences_module
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.preferences import Preferences, build_provider_order


MODEL_IDS = {
    "anthropic": "test-claude",
    "openai": "test-gpt",
    "gemini": "test-gemini",
    "ollama": "gemma3:1b",
}
CLOUD_ORDER = ["anthropic", "openai", "gemini"]


def preferences(**changes):
    values = {"mode": "auto", "cloud_order": list(CLOUD_ORDER), "models": dict(MODEL_IDS)}
    values.update(changes)
    return Preferences(**values)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("auto", ["anthropic", "openai", "gemini", "ollama"]),
        ("anthropic", ["anthropic", "openai", "gemini", "ollama"]),
        ("openai", ["openai", "anthropic", "gemini", "ollama"]),
        ("gemini", ["gemini", "anthropic", "openai", "ollama"]),
        ("ollama", ["ollama"]),
    ],
)
def test_provider_order(mode, expected):
    assert build_provider_order(preferences(mode=mode)) == expected


def test_custom_cloud_order_is_preserved():
    prefs = preferences(cloud_order=["gemini", "openai", "anthropic"])
    assert build_provider_order(prefs) == ["gemini", "openai", "anthropic", "ollama"]
    assert build_provider_order(prefs.model_copy(update={"mode": "openai"})) == [
        "openai", "gemini", "anthropic", "ollama"
    ]


@pytest.mark.parametrize(
    "order",
    [
        ["anthropic", "anthropic", "gemini"],
        ["anthropic", "openai"],
        ["anthropic", "openai", "unknown"],
        ["anthropic", "openai", "ollama"],
    ],
)
def test_cloud_order_requires_all_three_distinct_cloud_providers(order):
    with pytest.raises(ValidationError):
        preferences(cloud_order=order)


@pytest.mark.parametrize("model_id", ["", " ", "\t\n"])
def test_model_ids_cannot_be_blank(model_id):
    with pytest.raises(ValidationError):
        preferences(models={**MODEL_IDS, "ollama": model_id})


def test_model_map_requires_exactly_the_supported_providers():
    with pytest.raises(ValidationError):
        preferences(models={key: value for key, value in MODEL_IDS.items() if key != "gemini"})
    with pytest.raises(ValidationError):
        preferences(models={**MODEL_IDS, "unknown": "some-model"})


def test_unknown_mode_is_rejected():
    with pytest.raises(ValidationError):
        preferences(mode="unknown")


def test_saved_preferences_roundtrip_without_credentials(monkeypatch, tmp_path):
    settings_path = tmp_path / "model-settings.json"
    monkeypatch.setattr(preferences_module, "SETTINGS_PATH", settings_path)
    prefs = preferences(mode="openai", cloud_order=["gemini", "openai", "anthropic"])
    preferences_module.save_preferences(prefs)
    assert preferences_module.get_preferences() == prefs
    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert set(saved) == {"mode", "cloud_order", "models"}
    assert saved == prefs.model_dump()


@pytest.fixture
def configure_router(monkeypatch):
    """Use dummy credentials and a fresh circuit breaker, with no retry delay."""
    monkeypatch.setattr(router.settings, "anthropic_api_key", "test-anthropic-key")
    monkeypatch.setattr(router.settings, "openai_api_key", "test-openai-key")
    monkeypatch.setattr(router.settings, "google_api_key", "test-gemini-key")
    monkeypatch.setattr(router, "breaker", CircuitBreaker())

    async def no_sleep(_):
        pass

    monkeypatch.setattr(router.asyncio, "sleep", no_sleep)

    def configure(**changes):
        prefs = preferences(**changes)
        monkeypatch.setattr(router, "get_preferences", lambda: prefs)
        return prefs

    return configure


def http_error(status):
    request = httpx.Request("POST", "https://provider.invalid/test")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("provider unavailable", request=request, response=response)


@pytest.mark.asyncio
async def test_all_cloud_quotas_exhausted_falls_back_to_ollama(monkeypatch, configure_router):
    configure_router()
    # Same-provider alternate models are covered in tests/test_explain.py; this test is about
    # the provider order, so keep one model per provider.
    monkeypatch.setitem(router.config, "gemini_alternates", [])
    calls = []

    async def fake_complete(provider, model, *_args):
        calls.append((provider, model))
        if provider != "ollama":
            raise http_error(429)
        return "local answer"

    monkeypatch.setattr(router, "complete", fake_complete)
    answer, provider = await router.get_chat_model("answer").invoke("system", "question")
    assert (answer, provider) == ("local answer", "ollama")
    assert calls == [
        ("anthropic", MODEL_IDS["anthropic"]),
        ("anthropic", MODEL_IDS["anthropic"]),
        ("openai", MODEL_IDS["openai"]),
        ("openai", MODEL_IDS["openai"]),
        ("gemini", MODEL_IDS["gemini"]),
        ("gemini", MODEL_IDS["gemini"]),
        ("ollama", MODEL_IDS["ollama"]),
    ]


@pytest.mark.asyncio
async def test_missing_cloud_credentials_skip_directly_to_ollama(monkeypatch, configure_router):
    configure_router()
    monkeypatch.setattr(router.settings, "anthropic_api_key", "")
    monkeypatch.setattr(router.settings, "openai_api_key", "")
    monkeypatch.setattr(router.settings, "google_api_key", "")
    calls = []

    async def fake_complete(provider, *_args):
        calls.append(provider)
        return "local answer"

    monkeypatch.setattr(router, "complete", fake_complete)
    assert await router.get_chat_model("answer").invoke("system", "question") == ("local answer", "ollama")
    assert calls == ["ollama"]


@pytest.mark.asyncio
async def test_explicit_ollama_mode_never_calls_clouds(monkeypatch, configure_router):
    configure_router(mode="ollama")
    calls = []

    async def fake_complete(provider, model, *_args):
        calls.append((provider, model))
        return "local answer"

    monkeypatch.setattr(router, "complete", fake_complete)
    assert await router.get_chat_model("answer").invoke("system", "question") == ("local answer", "ollama")
    assert calls == [("ollama", "gemma3:1b")]


@pytest.mark.asyncio
async def test_final_ollama_is_attempted_even_while_its_circuit_is_cooling(monkeypatch, configure_router):
    configure_router()
    for _ in range(router.breaker.limit):
        router.breaker.fail("ollama")
    assert not router.breaker.available("ollama")
    calls = []

    async def fake_complete(provider, *_args):
        calls.append(provider)
        if provider != "ollama":
            raise http_error(429)
        return "recovered locally"

    monkeypatch.setattr(router, "complete", fake_complete)
    assert await router.get_chat_model("answer").invoke("system", "question") == ("recovered locally", "ollama")
    assert calls[-1] == "ollama"
    assert router.breaker.available("ollama")


@pytest.mark.parametrize("status", [400, 401, 403, 404])
@pytest.mark.asyncio
async def test_nonretryable_cloud_error_moves_to_next_provider(monkeypatch, configure_router, status):
    configure_router(mode="anthropic")
    calls = []

    async def fake_complete(provider, *_args):
        calls.append(provider)
        if provider == "anthropic":
            raise http_error(status)
        return "cloud answer"

    monkeypatch.setattr(router, "complete", fake_complete)
    assert await router.get_chat_model("answer").invoke("system", "question") == ("cloud answer", "openai")
    assert calls == ["anthropic", "openai"]


@pytest.mark.asyncio
async def test_preferences_are_read_once_per_model_invocation(monkeypatch, configure_router):
    initial = configure_router(mode="openai")
    reads = []
    calls = []

    def get_preferences():
        reads.append(1)
        return initial if len(reads) == 1 else preferences(mode="ollama")

    async def fake_complete(provider, model, *_args):
        calls.append((provider, model))
        if provider == "openai":
            raise http_error(401)
        return "answer"

    monkeypatch.setattr(router, "get_preferences", get_preferences)
    monkeypatch.setattr(router, "complete", fake_complete)
    assert await router.get_chat_model("answer").invoke("system", "question") == ("answer", "anthropic")
    assert len(reads) == 1
    assert calls == [("openai", MODEL_IDS["openai"]), ("anthropic", MODEL_IDS["anthropic"])]


@pytest.mark.parametrize("mode", ["auto", "anthropic"])
@pytest.mark.asyncio
async def test_selected_model_wins_over_legacy_task_config(monkeypatch, configure_router, mode):
    configure_router(mode=mode)
    monkeypatch.setitem(router.config, "tasks", {"answer": {"anthropic": "task-specific-claude"}})
    calls = []

    async def fake_complete(provider, model, *_args):
        calls.append((provider, model))
        return "answer"

    monkeypatch.setattr(router, "complete", fake_complete)
    assert await router.get_chat_model("answer").invoke("system", "question") == ("answer", "anthropic")
    assert calls == [("anthropic", MODEL_IDS["anthropic"])]


@pytest.mark.asyncio
async def test_concurrent_answers_keep_independent_frozen_preferences(monkeypatch, configure_router):
    configure_router()
    latest = preferences(mode="openai")
    monkeypatch.setattr(preferences_module, "get_preferences", lambda: latest)
    ready = {"one": asyncio.Event(), "two": asyncio.Event()}
    release = asyncio.Event()
    calls = []

    async def fake_complete(provider, model, messages, *_args):
        calls.append((messages[-1]["content"], provider, model))
        return "answer"

    async def answer(label):
        with preferences_module.model_request() as trace:
            ready[label].set()
            await release.wait()
            for _ in range(2):
                await router.get_chat_model("answer").invoke("system", label)
            return list(trace)

    monkeypatch.setattr(router, "complete", fake_complete)
    one = asyncio.create_task(answer("one"))
    await ready["one"].wait()
    latest = preferences(mode="gemini")
    two = asyncio.create_task(answer("two"))
    await ready["two"].wait()
    latest = preferences(mode="ollama")
    release.set()
    traces = await asyncio.gather(one, two)
    assert sorted(calls) == sorted([
        ("one", "openai", MODEL_IDS["openai"]),
        ("one", "openai", MODEL_IDS["openai"]),
        ("two", "gemini", MODEL_IDS["gemini"]),
        ("two", "gemini", MODEL_IDS["gemini"]),
    ])
    assert [[entry["provider"] for entry in trace] for trace in traces] == [["openai", "openai"], ["gemini", "gemini"]]
    assert preferences_module.request_preferences.get() is None
    assert preferences_module.request_trace.get() is None


def test_request_preferences_are_deep_copied_and_reset_after_error(monkeypatch):
    selected = preferences(mode="ollama")
    monkeypatch.setattr(preferences_module, "get_preferences", lambda: selected)
    with pytest.raises(RuntimeError):
        with preferences_module.model_request():
            selected.models["ollama"] = "other-model"
            assert preferences_module.request_preferences.get().models["ollama"] == MODEL_IDS["ollama"]
            raise RuntimeError("request failed")
    assert preferences_module.request_preferences.get() is None
    assert preferences_module.request_trace.get() is None
