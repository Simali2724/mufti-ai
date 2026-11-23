from app.retrieval.hybrid import fuse
from app.retrieval.bm25 import search
def test_fusion():
    r=fuse([('q','dense','same_concept',[{'id':'a','text':'A','dense_score':.8}]),
            ('q','bm25','same_concept',[{'id':'b','text':'B','bm25_score':4.},{'id':'a','text':'A','bm25_score':2.}])],5)
    assert r[0]['id']=='a';assert r[0]['dense_score']==.8
    # The lexical signal must survive fusion instead of being replaced by dense similarity.
    assert r[0]['lexical_score']==.5 and dict((c['id'],c['lexical_score']) for c in r)['b']==1.
    assert r[0]['relation']=='same_concept'

def test_related_concept_candidates_are_marked_not_merged():
    r=fuse([('related query','bm25','related_concept',[{'id':'x','text':'X','bm25_score':3.}])],5)
    assert r[0]['relation']=='related_concept'
def test_no_lexical_match(): assert search([{'id':'a','text':'History of Madinah'}],'quantum computing')==[]
def test_concurrent_chroma_initialization(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from app.retrieval import vector_store as v
    monkeypatch.setattr(v,'INDEX',tmp_path);monkeypatch.setattr(v,'_chroma_client',None)
    with ThreadPoolExecutor(max_workers=4) as pool: stores=list(pool.map(lambda _:v.ChromaStore(),range(8)))
    assert all(s.client is stores[0].client for s in stores)
    c={'id':'test','text':'A real source passage','book_id':'fixture','book_title':'Fixture','page_start':1,'page_end':1,'chapter':'','language':'English'}
    stores[0].upsert([c],[[1.,0.,0.]])
    assert stores[-1].search([1.,0.,0.],1)[0]['book_id']=='fixture'
import pytest
@pytest.mark.asyncio
async def test_query_embeddings_are_batched(monkeypatch):
    from app.retrieval import hybrid as h
    seen=[]
    async def embedding(queries): seen.append(queries);return [[1.,0.] for q in queries]
    class Store:
        def search(self,v,k): return []
    monkeypatch.setattr(h,'all_chunks',lambda:[{'id':'fixture','text':'History'}])
    monkeypatch.setattr(h,'embed',embedding);monkeypatch.setattr(h,'ChromaStore',Store)
    monkeypatch.setattr(h.settings,'enable_knowledge_graph',False)
    monkeypatch.setattr(h.segment_index,'load_segments',lambda:[])
    await h.search_local([{'text':'question','origin':'original','relation':'same_concept'},
                          {'text':'Urdu query','origin':'lexicon:x','relation':'same_concept'},
                          {'text':'English query','origin':'llm_translation','relation':'same_concept'}])
    assert seen==[['question','Urdu query','English query']]
@pytest.mark.asyncio
async def test_only_book_embeddings_are_persisted(tmp_path,monkeypatch):
    import json,httpx
    from collections import OrderedDict
    from app.retrieval import vector_store as v
    original=httpx.AsyncClient
    def handler(request):
        body=json.loads(request.content)
        return httpx.Response(200,json={'embeddings':[[1.,0.] for _ in body.get('input',[])]})
    monkeypatch.setattr(v,'INDEX',tmp_path);monkeypatch.setattr(v,'_query_vectors',OrderedDict())
    monkeypatch.setattr(v.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
    assert await v.embed(['A private question'])==[[1.,0.]]
    assert not (tmp_path/'embedding-cache').exists()
    await v.embed(['Book source passage'],persist=True)
    assert len(list((tmp_path/'embedding-cache').glob('*.json')))==1


def test_bm25_index_cache_does_not_serve_a_stale_corpus():
    """Caching the tokenised index must key on the actual corpus, not just its size."""
    from app.retrieval import bm25
    bm25.invalidate()
    filler = [{'id': f'f{i}', 'text': 'History of Madinah and the Constitution'} for i in range(4)]
    first = [*filler, {'id': 'b', 'text': 'Gender equality and the West'}]
    assert [c['id'] for c in bm25.search(first, 'gender equality', 5)] == ['b']
    # Same length, different documents under different ids: the cached index must be rebuilt.
    second = [{'id': 'c', 'text': 'Gender equality and the West'}, *filler]
    assert [c['id'] for c in bm25.search(second, 'gender equality', 5)] == ['c']
    # And the same corpus twice must reuse the index rather than rebuild it.
    built = []
    original = bm25.BM25Okapi
    bm25.BM25Okapi = lambda corpus: built.append(1) or original(corpus)
    try:
        bm25.search(second, 'history', 5)
    finally:
        bm25.BM25Okapi = original
    assert built == []
