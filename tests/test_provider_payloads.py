"""Exercise the real cloud adapters with offline HTTP responses and dummy keys."""

import json

import httpx
import pytest

from app.llm import providers


SCHEMA = {
    "type": "object",
    "properties": {"supported": {"type": "boolean"}},
    "required": ["supported"],
    "additionalProperties": False,
}
MESSAGES = [
    {"role": "system", "content": "Use only the supplied book excerpts."},
    {"role": "user", "content": "Is this claim supported?"},
    {"role": "assistant", "content": "Please provide an excerpt."},
    {"role": "user", "content": "The excerpt is supplied here."},
]


@pytest.fixture
def provider_http(monkeypatch):
    """Replace every AsyncClient transport so these tests cannot reach a service."""
    real_client = httpx.AsyncClient
    requests = []
    reply = {"status": 200, "body": {}}

    monkeypatch.setattr(providers.settings, "openai_api_key", "offline-openai-key")
    monkeypatch.setattr(providers.settings, "anthropic_api_key", "offline-anthropic-key")
    monkeypatch.setattr(providers.settings, "google_api_key", "offline-gemini-key")

    def handle(request):
        requests.append(request)
        return httpx.Response(reply["status"], json=reply["body"])

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handle)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client_factory)

    def respond(body, status=200):
        reply.update(body=body, status=status)
        return requests

    return respond


def payload(request):
    return json.loads(request.content)


@pytest.mark.asyncio
async def test_openai_uses_selected_model_and_strict_json_schema(provider_http):
    requests = provider_http({"choices": [{"message": {"content": '{"supported":true}'}}]})

    answer = await providers.complete("openai", "selected-gpt", MESSAGES, True, SCHEMA)

    assert json.loads(answer) == {"supported": True}
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.openai.com/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer offline-openai-key"
    body = payload(request)
    assert body["model"] == "selected-gpt"
    assert body["messages"] == MESSAGES
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "mufti_output", "strict": True, "schema": SCHEMA},
    }


@pytest.mark.asyncio
async def test_openai_json_mode_without_schema_remains_supported(provider_http):
    requests = provider_http({"choices": [{"message": {"content": '{"supported":false}'}}]})

    answer = await providers.complete("openai", "selected-gpt", MESSAGES, True)

    assert json.loads(answer) == {"supported": False}
    assert payload(requests[0])["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_anthropic_forces_schema_tool_and_reads_only_matching_tool(provider_http):
    expected = {"supported": True, "note": "کتاب"}
    schema = {
        **SCHEMA,
        "properties": {**SCHEMA["properties"], "note": {"type": "string"}},
        "required": ["supported", "note"],
    }
    requests = provider_http({
        "content": [
            {"type": "text", "text": "This prose must not become the structured result."},
            {"type": "tool_use", "name": "unrelated_tool", "input": {"supported": False}},
            {"type": "tool_use", "name": "mufti_output", "input": expected},
        ]
    })

    answer = await providers.complete("anthropic", "selected-claude", MESSAGES, True, schema)

    assert json.loads(answer) == expected
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.headers["x-api-key"] == "offline-anthropic-key"
    assert request.headers["anthropic-version"] == "2023-06-01"
    body = payload(request)
    assert body["model"] == "selected-claude"
    assert body["system"] == MESSAGES[0]["content"]
    assert body["messages"] == MESSAGES[1:]
    assert body["tool_choice"] == {"type": "tool", "name": "mufti_output"}
    assert len(body["tools"]) == 1
    assert body["tools"][0]["name"] == "mufti_output"
    assert body["tools"][0]["input_schema"] == schema


@pytest.mark.asyncio
async def test_anthropic_missing_forced_tool_rejects_unstructured_prose(provider_http):
    provider_http({"content": [{"type": "text", "text": '{"supported":true}'}]})

    with pytest.raises(ValueError, match="Missing structured result"):
        await providers.complete("anthropic", "selected-claude", MESSAGES, True, SCHEMA)


@pytest.mark.asyncio
async def test_anthropic_plain_answers_combine_text_blocks_without_tool_payloads(provider_http):
    requests = provider_http({"content": [
        {"type": "text", "text": "First sentence. "},
        {"type": "tool_use", "name": "other", "input": {"secret": "ignored"}},
        {"type": "text", "text": "Second sentence."},
    ]})

    answer = await providers.complete("anthropic", "selected-claude", MESSAGES)

    assert answer == "First sentence. Second sentence."
    assert "tools" not in payload(requests[0])
    assert "tool_choice" not in payload(requests[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["selected-gemini", "models/selected-gemini"])
async def test_gemini_sends_json_schema_and_omits_thought_parts(provider_http, model):
    requests = provider_http({"candidates": [{"content": {"parts": [
        {"text": "Private reasoning must not leak.", "thought": True},
        {"text": '{"supported":'},
        {"thoughtSignature": "opaque-signature"},
        {"text": "true}", "thought": False},
    ]}}]})

    answer = await providers.complete("gemini", model, MESSAGES, True, SCHEMA)

    assert answer == '{"supported":true}'
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://generativelanguage.googleapis.com/v1beta/models/selected-gemini:generateContent"
    assert request.headers["x-goog-api-key"] == "offline-gemini-key"
    body = payload(request)
    assert body["systemInstruction"] == {"parts": [{"text": MESSAGES[0]["content"]}]}
    assert [item["role"] for item in body["contents"]] == ["user", "model", "user"]
    assert [item["parts"][0]["text"] for item in body["contents"]] == [item["content"] for item in MESSAGES[1:]]
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseJsonSchema"] == SCHEMA


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
async def test_cloud_quota_error_reaches_router_as_http_status_error(provider_http, provider):
    requests = provider_http({"error": {"message": "Quota exhausted"}}, status=429)

    with pytest.raises(httpx.HTTPStatusError) as failure:
        await providers.complete(provider, "selected-model", MESSAGES, True, SCHEMA)

    assert failure.value.response.status_code == 429
    assert len(requests) == 1
