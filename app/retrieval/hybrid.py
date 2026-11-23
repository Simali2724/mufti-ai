"""Multi-query hybrid retrieval over child segments, preserving the lexical signal.

Each query variant runs BM25 and dense search independently. Results are fused with
reciprocal rank, but the per-retriever scores survive on every candidate so a later stage
can keep a strong exact-word hit that dense similarity alone would discard — the failure
that hid the gender-equality page behind generic rights pages.
"""
import asyncio
from app.core.config import settings
from app.core.logging import logger
from app.ingestion.indexer import all_chunks
from app.ingestion.graph_builder import related
from app.ingestion import segment_index
from app.retrieval.vector_store import ChromaStore, embed
from app.retrieval.bm25 import search as bm25
from app.retrieval import tree_nav

RRF_K = 60


def corpus():
    """Child segments when a validated build is active, else the page-level chunks."""
    segments = segment_index.load_segments()
    if segments:
        return segments, 'segments'
    return all_chunks(), 'pages'


def _blank(chunk):
    return {**chunk, 'rrf': 0.0, 'dense_score': 0.0, 'lexical_score': 0.0, 'graph_hits': 0,
            'tree_hits': 0,
            'matched_queries': [], 'relations': set()}


def fuse(rankings, limit):
    """rankings: list of (query, retriever, relation, results). Keeps every score source."""
    merged = {}
    best_lexical = max((c.get('bm25_score', 0) for _, _, _, results in rankings for c in results), default=0) or 1
    for query, retriever, relation, results in rankings:
        for rank, chunk in enumerate(results):
            item = merged.setdefault(chunk['id'], _blank(chunk))
            item['rrf'] += 1 / (RRF_K + rank + 1)
            item['dense_score'] = max(item['dense_score'], chunk.get('dense_score', 0) or 0)
            item['lexical_score'] = max(item['lexical_score'], (chunk.get('bm25_score', 0) or 0) / best_lexical)
            item['graph_hits'] += retriever == 'graph'
            item['tree_hits'] = item.get('tree_hits', 0) + (retriever == 'tree')
            item['scope_hits'] = item.get('scope_hits', 0) + (retriever == 'scope')
            item['matched_queries'].append({'query': query, 'retriever': retriever, 'rank': rank + 1,
                                            'relation': relation})
            item['relations'].add(relation)
    for item in merged.values():
        item['relation'] = 'same_concept' if 'same_concept' in item['relations'] else 'related_concept'
        item.pop('relations')
    return sorted(merged.values(), key=lambda c: c['rrf'], reverse=True)[:limit]


# A scoped dense search asks the vector index for this many times more neighbours and keeps the
# in-scope ones; Chroma has no page-range filter on the segment collection.
SCOPE_WIDEN = 12
# A scope this small (a section) also contributes its own segments in page order, so "summarise
# this section" sees the section from its first page even when few words match the question.
SCOPE_SWEEP_PAGES = 15


def in_scope(scope):
    """Predicate for ChatRequest.scope: one book, optionally one physical page range."""
    if not scope:
        return None
    book, start, end = scope.get('book_id'), scope.get('page_start'), scope.get('page_end')

    def keep(chunk):
        if book and chunk.get('book_id') != book:
            return False
        page = chunk.get('page_start') or chunk.get('page') or 0
        return (start is None or page >= start) and (end is None or page <= end)
    return keep


async def search_local(queries, limit=None, scope=None):
    """queries: [{'text','origin','relation'}]. Returns fused candidates, richest first.

    `scope` ({'book_id','page_start','page_end'}) restricts every route to that part of the
    library; the caller decides what to do when nothing in scope matches.
    """
    chunks, mode = corpus()
    limit = limit or settings.retrieval_candidates
    if not chunks:
        return [], {'mode': mode, 'corpus': 0, 'queries': []}
    keep = in_scope(scope)
    per_query = max(12, limit)
    texts = [q['text'] for q in queries]
    try:
        vectors = await embed(texts)
    except Exception as exc:
        logger.warning('dense embedding failed: %s; falling back to lexical search', exc)
        vectors = [None] * len(texts)
    rankings, report = [], []
    use_segments = mode == 'segments'
    store = None if use_segments else await asyncio.to_thread(ChromaStore)
    dense_k = per_query * SCOPE_WIDEN if keep else per_query
    if keep and scope.get('page_start') and scope.get('page_end') \
            and scope['page_end'] - scope['page_start'] < SCOPE_SWEEP_PAGES:
        sweep = sorted((c for c in chunks if keep(c)), key=lambda c: (c.get('page_start', 0), str(c['id'])))
        rankings.append(('scope', 'scope', 'same_concept', sweep[:per_query]))
    for query, vector in zip(queries, vectors):
        relation = query.get('relation', 'same_concept')
        lexical = await asyncio.to_thread(bm25, chunks, query['text'], per_query, keep)
        dense = []
        if vector is not None:
            try:
                dense = (await asyncio.to_thread(segment_index.search_segments, vector, dense_k) if use_segments
                         else await asyncio.to_thread(store.search, vector, dense_k))
                if keep:
                    dense = [c for c in dense if keep(c)][:per_query]
            except Exception as exc:
                logger.warning('dense search failed: %s', exc)
                dense = []
        rankings.append((query['text'], 'bm25', relation, lexical))
        rankings.append((query['text'], 'dense', relation, dense))
        # Third route: the PDF outline's clean section titles. Bounded, and it contributes
        # candidate pages only — see app/retrieval/tree_nav.py for why the body text cannot
        # be matched by a correctly spelled Urdu query on this book.
        tree, tree_report = ([], []) if not settings.enable_tree_route else             await asyncio.to_thread(tree_nav.segment_hits, chunks, query['text'])
        if keep:
            tree = [c for c in tree if keep(c)]
        if tree:
            rankings.append((query['text'], 'tree', relation, tree[:settings.tree_candidates]))
        report.append({'query': query['text'], 'origin': query.get('origin', ''), 'relation': relation,
                       'bm25_pages': [c['page_start'] for c in lexical[:8]],
                       'dense_pages': [c['page_start'] for c in dense[:8]],
                       'tree_pages': [c['page_start'] for c in tree[:8]],
                       'tree_sections': tree_report})
    if settings.enable_knowledge_graph:
        mapping = {c['id']: c for c in chunks}
        for query in queries[:2]:
            ids = await asyncio.to_thread(related, query['text'])
            hits = [mapping[i] for i in ids if i in mapping and (keep is None or keep(mapping[i]))]
            rankings.append((query['text'], 'graph', query.get('relation', 'same_concept'), hits))
    candidates = fuse(rankings, limit)
    return candidates, {'mode': mode, 'corpus': len(chunks), 'queries': report,
                        'candidate_pages': [c['page_start'] for c in candidates]}


async def search(queries, limit=None, scope=None):
    if isinstance(queries, str):
        queries = [{'text': queries, 'origin': 'original', 'relation': 'same_concept'}]
    if not settings.retriever_mcp_url or scope:
        # The MCP retrieval tool has no scope parameter, so a scoped request searches locally.
        return await search_local(queries, limit, scope)
    from mcp import ClientSession
    try:
        from mcp.client.streamable_http import streamable_http_client as transport
    except ImportError:
        from mcp.client.streamable_http import streamablehttp_client as transport
    import json
    async with transport(settings.retriever_mcp_url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            response = await session.call_tool('search_books', {'query': queries[0]['text'],
                                                                'top_k': limit or settings.retrieval_candidates})
            if getattr(response, 'isError', getattr(response, 'is_error', False)):
                raise RuntimeError('MCP retrieval failed')
            result = []
            for block in response.content:
                if hasattr(block, 'text'):
                    value = json.loads(block.text)
                    result.extend(value if isinstance(value, list) else [value])
            for item in result:
                item.setdefault('relation', 'same_concept')
                item.setdefault('matched_queries', [])
            logger.info('mcp retrieval returned %d', len(result))
            return result, {'mode': 'mcp', 'corpus': 0, 'queries': [{'query': queries[0]['text']}]}
