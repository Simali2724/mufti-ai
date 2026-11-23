"""Search warm-up and embedding keep-alive (loop 4, 2026-11-18)."""
import pytest
from app.core import warmup
from app.core.config import config


@pytest.mark.asyncio
async def test_warmup_touches_every_cold_stage(monkeypatch):
    from app.retrieval import hybrid, bm25, vector_store
    from app.ingestion import segment_index
    seen = []
    monkeypatch.setattr(hybrid, 'corpus', lambda: (seen.append('corpus') or [{'id': 'a', 'text': 'x'}], 'segments'))
    monkeypatch.setattr(bm25, 'search', lambda chunks, q, k=20, keep=None: seen.append('bm25') or [])

    async def fake_embed(texts, persist=False):
        seen.append('embed')
        return [[1.0, 0.0]]
    monkeypatch.setattr(vector_store, 'embed', fake_embed)
    monkeypatch.setattr(segment_index, 'search_segments', lambda v, k: seen.append('vector') or [])
    await warmup.warm()
    assert seen == ['corpus', 'bm25', 'embed', 'vector']
    assert warmup.STATE['status'] == 'ready' and 'total' in warmup.STATE['seconds']


@pytest.mark.asyncio
async def test_warmup_failure_is_recorded_not_raised(monkeypatch):
    from app.retrieval import hybrid

    def broken():
        raise ConnectionError('ollama down')
    monkeypatch.setattr(hybrid, 'corpus', broken)
    await warmup.warm()
    assert warmup.STATE['status'] == 'failed' and warmup.STATE['error'] == 'ConnectionError'


def test_keep_alive_is_long_for_cloud_and_short_for_local(monkeypatch):
    from app.retrieval import vector_store
    from app.agents import retriever_agent
    monkeypatch.setattr(retriever_agent, 'answering_provider', lambda: 'gemini')
    assert vector_store.embedding_keep_alive() == config.get('embedding_keep_alive_cloud', '30m')
    monkeypatch.setattr(retriever_agent, 'answering_provider', lambda: 'ollama')
    assert vector_store.embedding_keep_alive() == config.get('embedding_keep_alive_local', '5m')


def test_tests_never_start_the_real_warmup():
    from app.core.config import settings
    assert settings.warmup_on_start is False
