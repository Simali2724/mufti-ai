from typing import Protocol
import httpx,threading
from collections import OrderedDict
from app.core.config import settings,INDEX,config
_chroma_client=None
_chroma_lock=threading.Lock()
_query_vectors=OrderedDict()
class VectorStore(Protocol):
    def upsert(self,chunks,embeddings): ...
    def search(self,embedding,k): ...
def cache_write(path,text):
    """Best-effort cache write. The cache only saves re-embedding time, so a write the external
    D: drive refuses (measured 2026-11-16: intermittent OSError Errno 22 during write bursts)
    is retried briefly and then skipped instead of aborting a whole ingestion."""
    import time
    for attempt in range(4):
        try:
            path.write_text(text);return True
        except OSError:
            time.sleep(.25*(attempt+1))
    return False
def embedding_keep_alive():
    """How long Ollama keeps bge-m3 on the GPU after a search."""
    try:
        from app.agents.retriever_agent import answering_provider
        local=answering_provider()=='ollama'
    except Exception:
        local=True
    return config.get('embedding_keep_alive_local','5m') if local else config.get('embedding_keep_alive_cloud','30m')

def _use_gemini_embeddings():
    """Whether to use the Gemini Embedding API instead of local Ollama bge-m3.
    Cloud deployment sets EMBEDDING_PROVIDER=gemini in .env."""
    return settings.embedding_provider == 'gemini'

async def _embed_gemini(texts):
    """Call the Gemini Embedding API (text-embedding-004, 768 dimensions)."""
    import json
    from app.llm.preferences import request_api_keys
    gkey = (request_api_keys.get() or {}).get('gemini') or settings.google_api_key
    if not gkey:
        raise ValueError('GOOGLE_API_KEY required for Gemini embeddings')
    model = settings.gemini_embedding_model
    vectors = []
    # Gemini embedding API accepts batch of texts (up to 100 per call)
    batch_size = 100
    async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            payload = {
                'requests': [{'model': f'models/{model}', 'content': {'parts': [{'text': t}]}} for t in batch]
            }
            r = await client.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents',
                headers={'x-goog-api-key': gkey},
                json=payload
            )
            r.raise_for_status()
            for emb in r.json()['embeddings']:
                vectors.append(emb['values'])
    return vectors

async def embed(texts,persist=False):
    import json,hashlib
    cache=INDEX/'embedding-cache'
    if persist: cache.mkdir(exist_ok=True)
    model_tag = settings.gemini_embedding_model if _use_gemini_embeddings() else settings.embedding_model
    keys=[hashlib.sha256((model_tag+'\0'+t).encode()).hexdigest() for t in texts]
    vectors=[json.loads((cache/(key+'.json')).read_text()) if persist and (cache/(key+'.json')).exists() else _query_vectors.get(key) if not persist else None for key in keys]
    missing=[i for i,v in enumerate(vectors) if v is None]
    if not missing: return vectors

    if _use_gemini_embeddings():
        new_vectors = await _embed_gemini([texts[i] for i in missing])
        for i, v in zip(missing, new_vectors):
            vectors[i] = v
            if persist: cache_write(cache / (keys[i] + '.json'), json.dumps(v))
            else:
                _query_vectors[keys[i]] = v
                while len(_query_vectors) > 128: _query_vectors.popitem(last=False)
        return vectors

    # Local Ollama path (original)
    async with httpx.AsyncClient(timeout=300,trust_env=False) as client:
        from app.core.resources import ollama_lock,select_model
        async with ollama_lock:
            await select_model(client,settings.embedding_model)
            r=await client.post(settings.ollama_base_url+'/api/embed',json={'model':settings.embedding_model,'input':[texts[i] for i in missing],'truncate':True,'keep_alive':embedding_keep_alive(),'options':{'num_gpu':config.get('embedding_num_gpu',99),'num_thread':4}})
        r.raise_for_status()
        for i,v in zip(missing,r.json()['embeddings']):
            vectors[i]=v
            if persist: cache_write(cache/(keys[i]+'.json'),json.dumps(v))
            else:
                _query_vectors[keys[i]]=v
                while len(_query_vectors)>128: _query_vectors.popitem(last=False)
        return vectors
class ChromaStore:
    def __init__(self):
        global _chroma_client
        import chromadb
        from chromadb.config import Settings
        with _chroma_lock:
            if _chroma_client is None: _chroma_client=chromadb.PersistentClient(path=str(INDEX/'chroma'),settings=Settings(anonymized_telemetry=False))
            self.client=_chroma_client
        self.collection=self.client.get_or_create_collection('books',metadata={'hnsw:space':'cosine'})
    def upsert(self,chunks,embeddings):
        self.collection.upsert(ids=[c['id'] for c in chunks],documents=[c['text'] for c in chunks],embeddings=embeddings,metadatas=[{k:v for k,v in c.items() if k not in ['id','text']} for c in chunks])
    def delete_book(self,book_id): self.collection.delete(where={'book_id':book_id})
    def search(self,embedding,k):
        if not self.collection.count(): return []
        r=self.collection.query(query_embeddings=[embedding],n_results=min(k,self.collection.count()))
        return [{'id':i,'text':t,**m,'dense_score':1-d} for i,t,m,d in zip(r['ids'][0],r['documents'][0],r['metadatas'][0],r['distances'][0])]
