"""Reproduce the PREVIOUS retrieval/selection behaviour for an honest before/after number.

This replays the algorithm that shipped before the coverage repair: one query plus the old
name-alias variants, reciprocal-rank fusion over page-level chunks, a relevance score equal
to the dense similarity, a hard 0.42 floor on that score, retrieval_top_k survivors, and the
answering model seeing only the first three.

Caveat recorded with the results: the old pipeline also added a model-produced Urdu/English
translation when a rewrite call succeeded. That call is not replayed here because it costs
over a minute per question on the local fallback. In the captured live trace of the failing
question the translation variant did not change the outcome — the reviewed page still ranked
fourth and was cut by the three-passage limit.
"""
import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings  # noqa: E402
from app.ingestion.indexer import all_chunks  # noqa: E402
from app.ingestion.graph_builder import related  # noqa: E402
from app.retrieval.bm25 import search as bm25  # noqa: E402
from app.retrieval.vector_store import ChromaStore, embed  # noqa: E402
from eval.run_benchmark import load_cases, _rate, _median  # noqa: E402

OLD_TOP_K = 6
OLD_THRESHOLD = .42
OLD_ANSWER_PASSAGES = 3


def old_expand(query):
    canonical = re.sub(r'\b(?:mahomet|mohammed|mohammad|muhammed)\b', 'Muhammad', query, flags=re.I)
    variants = []
    if re.search(r'\b(?:muhammad|prophet)\b', canonical, re.I):
        variants.append('حضرت محمد رسول اللہ سیرت ' + canonical)
    return canonical, variants


def old_fuse(rankings, k):
    merged = {}
    for results in rankings:
        for rank, c in enumerate(results):
            item = merged.setdefault(c['id'], {**c, 'rrf': 0, 'dense_score': 0})
            item['rrf'] += 1 / (60 + rank + 1)
            item['dense_score'] = max(item.get('dense_score', 0), c.get('dense_score', 0))
    return sorted(merged.values(), key=lambda c: c['rrf'], reverse=True)[:k]


async def old_search(query):
    chunks = all_chunks()
    k = OLD_TOP_K
    canonical, variants = old_expand(query)
    queries = list(dict.fromkeys([canonical] + variants))[:3]
    store = ChromaStore()
    vectors = await embed(queries)
    rankings = []
    for q, vector in zip(queries, vectors):
        rankings.append(bm25(chunks, q, k * 3))
        rankings.append(store.search(vector, k * 3))
    if settings.enable_knowledge_graph:
        mapping = {c['id']: c for c in chunks}
        rankings.append([mapping[i] for i in related(canonical) if i in mapping])
    fused = old_fuse(rankings, k * 3)
    scored = [{**c, 'relevance': c.get('dense_score', 0)} for c in fused]
    kept = sorted([c for c in scored if c['relevance'] >= OLD_THRESHOLD],
                  key=lambda c: (c.get('rrf', c['relevance']), c['relevance']), reverse=True)[:OLD_TOP_K]
    return fused, kept


async def main():
    cases = load_cases(include_holdout=True)
    rows = []
    for case in cases:
        started = time.monotonic()
        fused, kept = await old_search(case['question'])
        expected = set(case['expected_pages'])
        kept_pages = [c['page_start'] for c in kept]
        rows.append({'id': case['id'], 'expectation': case['expectation'],
                     'expected_pages': sorted(expected),
                     'candidate_pages': [c['page_start'] for c in fused],
                     'selected_pages': kept_pages,
                     'answer_pages': kept_pages[:OLD_ANSWER_PASSAGES],
                     'candidate_hit': bool(expected & {c['page_start'] for c in fused}),
                     'selected_hit': bool(expected & set(kept_pages)),
                     'answer_hit': bool(expected & set(kept_pages[:OLD_ANSWER_PASSAGES])),
                     'seconds': round(time.monotonic() - started, 2)})
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    answerable = [r for r in rows if r['expectation'] != 'absent']
    summary = {'mode': 'baseline-retrieval', 'cases': len(rows), 'answerable': len(answerable),
               'candidate_recall': _rate(r['candidate_hit'] for r in answerable),
               'selected_recall': _rate(r['selected_hit'] for r in answerable),
               'recall_in_passages_sent_to_the_model': _rate(r['answer_hit'] for r in answerable),
               'median_seconds': _median([r['seconds'] for r in rows]),
               'misses_at_answer_stage': [r['id'] for r in answerable if not r['answer_hit']]}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    Path(__file__).with_name('benchmark-baseline.json').write_text(
        json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
