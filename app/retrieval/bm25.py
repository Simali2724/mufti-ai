"""Lexical retrieval over the active corpus, with the tokenised index cached.

Building BM25Okapi tokenises the whole corpus. Each request runs several query variants and
the corpus only changes when the index is rebuilt or the segment build is switched, so the
index is cached and reused instead of being rebuilt once per variant. Ranking is unchanged:
the same corpus and the same query produce the same scores as before.
"""
import hashlib
import threading
from rank_bm25 import BM25Okapi
from app.ingestion.normalize import tokens

_lock = threading.Lock()
_cache = {'key': None, 'index': None}


def _key(chunks):
    """Identity for a corpus. Hashing the ids costs a millisecond; tokenising costs seconds,
    and a weaker key would silently serve a stale index after a re-index."""
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(str(chunk['id']).encode('utf-8', 'replace'))
        digest.update(b'\0')
    return len(chunks), digest.hexdigest()


def _index(chunks):
    key = _key(chunks)
    with _lock:
        if _cache['key'] != key:
            _cache['index'] = BM25Okapi([tokens(c['text']) or ['_empty_'] for c in chunks])
            _cache['key'] = key
        return _cache['index']


def invalidate():
    """Drop the cached index; call after re-indexing or switching the segment build."""
    with _lock:
        _cache.update(key=None, index=None)


def search(chunks, query, k=20, keep=None):
    """Top-k BM25 hits. `keep(chunk)` restricts the result (scoped search) WITHOUT building a
    second index: scores are still computed over the whole corpus, so IDF and the cache are
    unchanged and a scoped request does not evict the full-corpus index."""
    if not chunks:
        return []
    scores = _index(chunks).get_scores(tokens(query))
    candidates = range(len(chunks)) if keep is None else [i for i in range(len(chunks)) if keep(chunks[i])]
    order = sorted(candidates, key=lambda i: scores[i], reverse=True)[:k]
    return [{**chunks[i], 'bm25_score': float(scores[i])} for i in order if scores[i] > 0]
