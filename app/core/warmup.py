"""Warm the search stack in the background when the server starts (loop 4, 2026-11-18).

Measured on this machine, in one fresh process (profile in VERIFICATION.md):
    import 4.0 s · bge-m3 load 10-19 s · first Chroma query 7.6 s · first full search 7.2 s
    → the same search warm: 0.33 s
The first reader question after a restart used to pay all of it (retrieve stage 42.5 s in the
live trace of 2026-11-17 23:59). Warming runs as a background task, so the server is reachable
at once; a question that arrives during warm-up simply waits on the same locks as before.
Failures (Ollama not running yet) are recorded, never raised.
"""
import asyncio
import time
from app.core.logging import logger

STATE = {'status': 'not_started', 'seconds': {}, 'error': ''}


async def warm():
    STATE.update(status='running', seconds={}, error='')
    started = time.monotonic()

    def mark(name, since):
        STATE['seconds'][name] = round(time.monotonic() - since, 2)
        return time.monotonic()

    try:
        from app.ingestion import segment_index
        from app.retrieval import bm25, hybrid
        from app.retrieval.vector_store import embed, _use_gemini_embeddings
        t = time.monotonic()
        chunks, _mode = await asyncio.to_thread(hybrid.corpus)
        t = mark('corpus', t)
        await asyncio.to_thread(bm25.search, chunks, 'warm up', 1)
        t = mark('bm25_index', t)
        # In cloud mode (Gemini embeddings), skip the warmup embedding call to save quota
        if not _use_gemini_embeddings():
            vector = (await embed(['warm up the search model']))[0]
            t = mark('embedding_model', t)
            await asyncio.to_thread(segment_index.search_segments, vector, 1)
            mark('vector_index', t)
        STATE['status'] = 'ready'
    except Exception as exc:  # Ollama may simply not be running yet
        STATE.update(status='failed', error=type(exc).__name__)
        logger.warning('search warm-up failed: %s', type(exc).__name__)
    STATE['seconds']['total'] = round(time.monotonic() - started, 2)
    logger.info('search warm-up %s in %.1fs', STATE['status'], STATE['seconds']['total'])
