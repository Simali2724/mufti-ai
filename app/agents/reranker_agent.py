from app.retrieval.reranker import rerank
async def run(s):
    return {'reranked_chunks':await rerank(s.get('retrieval_query',s['user_input']),s.get('retrieved_chunks',[]))}
