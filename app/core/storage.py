import sqlite3,asyncio
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
class LocalSqliteSaver(AsyncSqliteSaver):
    async def setup(self):
        async with self.lock:
            if self.is_setup: return
            await self.conn.execute('PRAGMA busy_timeout=30000')
            await self.conn.execute('PRAGMA journal_mode=DELETE')
            await self.conn.execute('PRAGMA synchronous=FULL')
            await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
                checkpoint_id TEXT NOT NULL, parent_checkpoint_id TEXT,
                type TEXT, checkpoint BLOB, metadata BLOB,
                PRIMARY KEY (thread_id,checkpoint_ns,checkpoint_id));
            CREATE TABLE IF NOT EXISTS writes (
                thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
                checkpoint_id TEXT NOT NULL, task_id TEXT NOT NULL,
                task_path TEXT NOT NULL DEFAULT '', idx INTEGER NOT NULL,
                channel TEXT NOT NULL, type TEXT, value BLOB,
                PRIMARY KEY (thread_id,checkpoint_ns,checkpoint_id,task_id,idx));
            """)
            async with self.conn.execute('PRAGMA table_info(writes)') as cur:
                columns=[r[1] for r in await cur.fetchall()]
            if 'task_path' not in columns:
                await self.conn.execute("ALTER TABLE writes ADD COLUMN task_path TEXT NOT NULL DEFAULT ''")
            await self.conn.commit()
            self._has_task_path=True
            self.is_setup=True
class ScopedSqliteSaver(BaseCheckpointSaver):
    """Keep no database handle open while a model is generating."""
    get_next_version=AsyncSqliteSaver.get_next_version
    def __init__(self,path):
        super().__init__()
        self.path=str(path);self.lock=asyncio.Lock()
    async def _run(self,method,*args,**kwargs):
        async with self.lock:
            for attempt in range(3):
                try:
                    async with LocalSqliteSaver.from_conn_string(self.path) as saver:
                        await saver.setup()
                        return await getattr(saver,method)(*args,**kwargs)
                except sqlite3.OperationalError as exc:
                    if attempt==2 or not any(term in str(exc).lower() for term in ['i/o','locked','busy']): raise
                    await asyncio.sleep(.1*(2**attempt))
    async def aget_tuple(self,config): return await self._run('aget_tuple',config)
    async def aput(self,config,checkpoint,metadata,new_versions):
        return await self._run('aput',config,checkpoint,metadata,new_versions)
    async def aput_writes(self,config,writes,task_id,task_path=''):
        await self._run('aput_writes',config,writes,task_id,task_path)
    async def adelete_thread(self,thread_id): await self._run('adelete_thread',thread_id)
    async def alist(self,config,*,filter=None,before=None,limit=None):
        async with self.lock:
            async with LocalSqliteSaver.from_conn_string(self.path) as saver:
                await saver.setup()
                async for item in saver.alist(config,filter=filter,before=before,limit=limit): yield item
def storage_status(index):
    path=index/'sessions.sqlite'
    if not path.exists(): return 'not_initialized'
    try:
        conn=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)
        try: conn.execute('SELECT 1 FROM checkpoints LIMIT 1').fetchone()
        finally: conn.close()
        return 'ok'
    except sqlite3.Error: return 'unavailable'
