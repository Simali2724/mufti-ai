import asyncio,math
from app.core.config import settings,config
_model=None
async def rerank(query,chunks):
    if settings.enable_reranker:
        def run():
            global _model
            from sentence_transformers import CrossEncoder
            if _model is None: _model=CrossEncoder(config['reranker_model'])
            scores=_model.predict([(query,c['text']) for c in chunks])
            return [{**c,'relevance':1/(1+math.exp(-float(s)))} for c,s in zip(chunks,scores)]
        chunks=await asyncio.to_thread(run) if chunks else []
    else:
        chunks=[{**c,'relevance':c.get('dense_score',0)} for c in chunks]
    # Without a real cross-encoder, keep hybrid lexical/semantic ordering.
    # Sorting only by dense similarity discards the exact-word search signal.
    key=(lambda c:c['relevance']) if settings.enable_reranker else (lambda c:(c.get('rrf',c['relevance']),c['relevance']))
    return sorted([c for c in chunks if c['relevance']>=settings.rerank_threshold],key=key,reverse=True)[:settings.retrieval_top_k]
