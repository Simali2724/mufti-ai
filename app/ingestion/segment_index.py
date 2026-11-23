"""Staged child-segment index: built beside the live index, validated, then activated.

The live page-level Chroma collection is never touched. A build writes into
data/index/segments/<build-id>/ and only becomes active when `activate` succeeds, so the
previous build stays on disk for rollback. Switching the embedding model invalidates every
build: a build records its model and retrieval refuses to use a mismatched one.
"""
import asyncio
import json
import time
from app.core.config import INDEX, settings
from app.ingestion.indexer import catalog, read_json
from app.ingestion.segments import page_units, corrections_for, quality

SEGMENTS_DIR = INDEX / 'segments'
ACTIVE_POINTER = SEGMENTS_DIR / 'active.json'


def active_build():
    """The activated build, or None when there is no compatible one."""
    if not ACTIVE_POINTER.exists():
        return None
    try:
        record = json.loads(ACTIVE_POINTER.read_text(encoding='utf-8'))
    except ValueError:
        return None
    if record.get('embedding_model') != settings.embedding_model and record.get('embedding_model') != settings.gemini_embedding_model:
        return None
    if not (SEGMENTS_DIR / record['build_id'] / 'segments.json').exists():
        return None
    return record


def build_dir(build_id):
    return SEGMENTS_DIR / build_id


_cache = {'build_id': None, 'segments': None, 'by_id': None, 'by_parent': None, 'by_page': None}


def load_segments():
    """Activated segments, cached by build id. Returns [] when no build is active."""
    record = active_build()
    if record is None:
        return []
    if _cache['build_id'] != record['build_id']:
        rows = json.loads((build_dir(record['build_id']) / 'segments.json').read_text(encoding='utf-8'))
        by_parent, by_page = {}, {}
        for row in rows:
            by_parent.setdefault(row['parent_id'], row['parent_text'])
            by_page.setdefault((row['book_id'], row['page_start']), []).append(row)
        _cache.update(build_id=record['build_id'], segments=rows, by_id={r['id']: r for r in rows},
                      by_parent=by_parent, by_page=by_page)
    return _cache['segments']


def parent_text(parent_id):
    load_segments()
    return (_cache['by_parent'] or {}).get(parent_id, '')


def page_parents(book_id, page):
    """Parent texts on one physical page, in reading order."""
    load_segments()
    rows = (_cache['by_page'] or {}).get((book_id, page), [])
    seen, out = set(), []
    for row in sorted(rows, key=lambda r: r['parent_index']):
        if row['parent_id'] in seen:
            continue
        seen.add(row['parent_id'])
        out.append(row['parent_text'])
    return out


def collection_for(build_id):
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(build_dir(build_id) / 'chroma'),
                                       settings=Settings(anonymized_telemetry=False))
    return client.get_or_create_collection('segments', metadata={'hnsw:space': 'cosine'})


def search_segments(embedding, k):
    record = active_build()
    if record is None:
        return []
    collection = collection_for(record['build_id'])
    total = collection.count()
    if not total:
        return []
    result = collection.query(query_embeddings=[embedding], n_results=min(k, total))
    load_segments()
    out = []
    for identifier, document, distance in zip(result['ids'][0], result['documents'][0], result['distances'][0]):
        row = (_cache['by_id'] or {}).get(identifier)
        if row:
            out.append({**row, 'dense_score': 1 - distance})
    return out


def build_rows():
    rows, audit = [], []
    corrections_by_book = {}
    for book in catalog():
        corrections_by_book[book['id']] = corrections_for(book['id'])
        for page in read_json(f"pages-{book['id']}.json", []):
            measure = quality(page.get('text', ''))
            audit.append({'book_id': book['id'], 'page': page['page'], 'ocr': page.get('ocr', False),
                          'warning': page.get('warning', ''), 'corrected': page['page'] in corrections_by_book[book['id']],
                          **measure})
            rows.extend(page_units(page, book, corrections_by_book[book['id']]))
    return rows, audit


async def build(progress=print):
    """Embed every child segment into a fresh staged build. Returns the build record."""
    from app.retrieval.vector_store import embed
    build_id = time.strftime('%Y%m%d-%H%M%S')
    target = build_dir(build_id)
    target.mkdir(parents=True, exist_ok=True)
    rows, audit = build_rows()
    (INDEX / 'extraction-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding='utf-8')
    progress(f'segments={len(rows)} pages_audited={len(audit)} build={build_id}')
    collection = collection_for(build_id)
    started = time.monotonic()
    for start in range(0, len(rows), 8):
        batch = rows[start:start + 8]
        vectors = await embed([r['text'] for r in batch], persist=True)
        collection.upsert(ids=[r['id'] for r in batch], documents=[r['text'] for r in batch], embeddings=vectors,
                          metadatas=[{'page_start': r['page_start'], 'parent_id': r['parent_id']} for r in batch])
        if start % 200 == 0:
            done = start + len(batch)
            rate = done / max(.1, time.monotonic() - started)
            progress(f'embedded {done}/{len(rows)} ({rate:.1f}/s, eta {int((len(rows) - done) / max(.01, rate))}s)')
    (target / 'segments.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    _embedding_tag = settings.gemini_embedding_model if settings.embedding_provider == 'gemini' else settings.embedding_model
    record = {'build_id': build_id, 'embedding_model': _embedding_tag, 'segments': len(rows),
              'pages': len({(r['book_id'], r['page_start']) for r in rows}),
              'created': time.strftime('%Y-%m-%dT%H:%M:%S'), 'seconds': round(time.monotonic() - started, 1)}
    (target / 'build.json').write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding='utf-8')
    return record


def validate(build_id, probes=()):
    """Structural checks plus optional (query, expected_page) lexical probes."""
    target = build_dir(build_id)
    issues = []
    if not (target / 'segments.json').exists():
        return {'ok': False, 'issues': ['segments.json missing']}
    rows = json.loads((target / 'segments.json').read_text(encoding='utf-8'))
    collection = collection_for(build_id)
    if collection.count() != len(rows):
        issues.append(f'vector count {collection.count()} != segment count {len(rows)}')
    if len({r['id'] for r in rows}) != len(rows):
        issues.append('duplicate segment ids')
    source_pages = {(b['id'], p['page']) for b in catalog() for p in read_json(f"pages-{b['id']}.json", []) if p.get('text', '').strip()}
    covered = {(r['book_id'], r['page_start']) for r in rows}
    missing = source_pages - covered
    if missing:
        issues.append(f'{len(missing)} readable pages produced no segment')
    # A child must be a contiguous run of its parent. Line breaks legitimately become spaces
    # during chunking, so compare with whitespace collapsed; anything else means the chunker
    # dropped, reordered or duplicated source text and quotes from it could not be trusted.
    import re as _re
    def flat(text):
        return _re.sub(r'\s+', ' ', text).strip()
    detached = [row['id'] for row in rows if flat(row['text']) not in flat(row['parent_text'])]
    if detached:
        issues.append(f'{len(detached)} children not contained in their parent, '
                      f'first: {", ".join(detached[:5])}')
    from app.ingestion.normalize import tokens
    for query, page in probes:
        wanted = set(tokens(query))
        hit = any(r['page_start'] == page and wanted & set(tokens(r['text'])) for r in rows)
        if not hit:
            issues.append(f'probe {query!r} found no lexical overlap on page {page}')
    return {'ok': not issues, 'issues': issues, 'segments': len(rows), 'pages': len(covered)}


def activate(build_id):
    record = json.loads((build_dir(build_id) / 'build.json').read_text(encoding='utf-8'))
    previous = active_build()
    record['previous_build_id'] = previous['build_id'] if previous else None
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_POINTER.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding='utf-8')
    _cache['build_id'] = None
    return record


def rollback():
    """Return to the previous build, or deactivate segments entirely (page index still works)."""
    record = active_build()
    previous = (record or {}).get('previous_build_id')
    if previous and (build_dir(previous) / 'build.json').exists():
        return activate(previous)
    ACTIVE_POINTER.unlink(missing_ok=True)
    _cache['build_id'] = None
    return None


if __name__ == '__main__':
    import argparse
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['build', 'validate', 'activate', 'rollback', 'status'])
    parser.add_argument('--build-id', default='')
    args = parser.parse_args()
    if args.command == 'build':
        built = asyncio.run(build())
        print(json.dumps(built, indent=1))
        print(json.dumps(validate(built['build_id']), indent=1, ensure_ascii=False))
    elif args.command == 'validate':
        print(json.dumps(validate(args.build_id), indent=1, ensure_ascii=False))
    elif args.command == 'activate':
        print(json.dumps(activate(args.build_id), indent=1))
    elif args.command == 'rollback':
        print(json.dumps(rollback(), indent=1))
    else:
        print(json.dumps({'active': active_build(),
                          'builds': sorted(p.name for p in SEGMENTS_DIR.glob('*/') if (p / 'build.json').exists())}, indent=1))
