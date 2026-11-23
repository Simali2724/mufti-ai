import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.agents import graph as g
from app.core.schemas import ChatRequest
@pytest.mark.asyncio
async def test_fresh_connections_keep_history(tmp_path,monkeypatch):
    monkeypatch.setattr(g,'INDEX',tmp_path)
    service=g.PersistentGraph()
    result=await g.ask(service,ChatRequest(question='Hello',session_id='storage-regression'))
    assert 'Assalamu' in result.answer
    state=await service.aget_state({'configurable':{'thread_id':'storage-regression'}})
    assert state.values['history'][0]['question']=='Hello'
    conn=sqlite3.connect(tmp_path/'sessions.sqlite')
    try: mode=conn.execute('PRAGMA journal_mode').fetchone()
    finally: conn.close()
    assert mode[0]=='delete'
    await service.checkpointer.adelete_thread('storage-regression')
    state=await service.aget_state({'configurable':{'thread_id':'storage-regression'}})
    assert not state.values.get('history')
def test_storage_failure_returns_retryable_error(tmp_path,monkeypatch):
    from app.main import app
    monkeypatch.setattr(g,'INDEX',tmp_path)
    async def fail(self,data,config): raise sqlite3.OperationalError('simulated I/O failure')
    monkeypatch.setattr(g.PersistentGraph,'ainvoke',fail)
    with TestClient(app) as client:
        r=client.post('/chat',json={'question':'Hello','session_id':'io-regression'})
    assert r.status_code==503
    assert 'Please retry' in r.json()['detail']
@pytest.mark.asyncio
async def test_checkpoint_reopens_after_io_error(tmp_path,monkeypatch):
    from contextlib import asynccontextmanager
    from app.core.storage import LocalSqliteSaver,ScopedSqliteSaver
    opened=[]
    @asynccontextmanager
    async def factory(path):
        opened.append(path)
        class Saver:
            async def setup(self): pass
            async def aget_tuple(self,config):
                if len(opened)==1: raise sqlite3.OperationalError('simulated disk I/O error')
                return None
        yield Saver()
    monkeypatch.setattr(LocalSqliteSaver,'from_conn_string',factory)
    result=await ScopedSqliteSaver(tmp_path/'checkpoint.sqlite').aget_tuple({'configurable':{'thread_id':'retry'}})
    assert result is None and len(opened)==2


def test_frontend_files_are_revalidated_not_cached():
    """2026-11-18: a cached tour.js hid new features after an update."""
    from app.main import app
    with TestClient(app) as client:
        for path in ('/', '/app.js', '/tour.js', '/style.css'):
            r = client.get(path)
            assert r.status_code == 200 and r.headers.get('cache-control') == 'no-cache', path
