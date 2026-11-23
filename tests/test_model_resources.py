import httpx
import pytest
from app.core import resources
from app.agents import formatter

@pytest.mark.asyncio
async def test_first_embedding_does_not_unload_uninstalled_default(monkeypatch):
    monkeypatch.setattr(resources, 'current_model', None)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await resources.select_model(client, 'bge-m3')
    assert calls == []
    assert resources.current_model == 'bge-m3'

@pytest.mark.asyncio
@pytest.mark.parametrize('status', [200, 404, 500])
async def test_switch_handles_removed_model_but_preserves_service_errors(monkeypatch, status):
    monkeypatch.setattr(resources, 'current_model', 'removed-model')
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status))) as client:
        if status == 500:
            with pytest.raises(httpx.HTTPStatusError):
                await resources.select_model(client, 'bge-m3')
            assert resources.current_model == 'removed-model'
        else:
            await resources.select_model(client, 'bge-m3')
            assert resources.current_model == 'bge-m3'

@pytest.mark.parametrize('language', ['English', 'Hindi', 'Urdu', 'Hinglish'])
def test_search_failure_is_not_missing_book_evidence(language):
    from app.core.language import SEARCH_UNAVAILABLE
    result = formatter.run({'detected_language': language, 'intent': 'book_question',
        'user_input': 'Question', 'retrieval_failed': True,
        'errors': ['Retrieval unavailable: HTTPStatusError']})
    assert result['reason_code'] == 'retrieval_unavailable'
    assert result['final_answer'] == SEARCH_UNAVAILABLE[language]
    assert not result['grounded']
    assert result['citations'] == []


@pytest.mark.parametrize('language', ['English', 'Hindi', 'Urdu', 'Hinglish'])
def test_answer_model_failure_is_not_missing_book_evidence(language):
    from app.core.language import PROVIDER_UNAVAILABLE, NOT_FOUND
    result = formatter.run({'detected_language': language, 'intent': 'book_question',
        'user_input': 'Question',
        'evidence_windows': [{'source_id': 1, 'page_start': 3, 'book_id': 'b', 'book_title': 'T',
                              'text': 'A passage', 'spans': [{'span_id': 1, 'text': 'A passage'}],
                              'relation': 'same_concept'}],
        'errors': ['Answer unavailable: HTTPStatusError']})
    assert result['reason_code'] in ('provider_unavailable', 'provider_quota_exhausted')
    assert PROVIDER_UNAVAILABLE[language] in result['final_answer']
    assert result['final_answer'] != NOT_FOUND[language]
    assert not result['grounded']
