"""Bounded navigation route: match the question against clean section titles, not OCR.

The third retrieval route beside lexical and semantic search over the body text. It exists
because of a measurable asymmetry in this book: the body text is OCR over legacy InPage
fonts and is degraded, while the PDF outline's section titles are embedded text and are
correctly spelled. PDF page 280's body reads "آینی مساوات کا جق"; its outline title reads
"آئینی مساوات کا حق". A reader typing correct Urdu can match the second and not the first.

What this route returns is deliberately weak: candidate PAGES, never evidence. A heading
locates a section; it is not support for anything asserted inside it. Candidates coming from
here are read from the real paragraphs on those pages and still have to survive the same
ranking, the same floors and the same per-claim verification as any other candidate, so a
wrong tree decision can add noise but cannot displace strong lexical evidence or produce an
unverified claim.

It is bounded on purpose: at most `TREE_NODES` matched sections per query variant and at
most `TREE_PAGES` pages drawn from them, because a chapter-level node can span forty pages
and pulling all of their segments in would swamp the candidate pool.
"""
from app.ingestion import book_tree, segment_index
from app.ingestion.normalize import tokens

TREE_NODES = 3
TREE_PAGES = 8
# A section title is short, so a single shared content word is a weak signal. Require either
# a multi-word overlap or a high share of the title's own words.
MIN_SHARED = 2
MIN_SHARE = .5


def score_title(query_tokens, title):
    """Overlap between the question and one section title, normalised by title length."""
    title_tokens = [t for t in tokens(title) if len(t) > 1]
    if not title_tokens:
        return 0.0, 0
    shared = sum(token in query_tokens for token in title_tokens)
    return shared / len(title_tokens), shared


def match_nodes(book_id, query, limit=TREE_NODES):
    """Sections whose clean title the question actually overlaps, best first."""
    query_tokens = set(t for t in tokens(query) if len(t) > 1)
    if not query_tokens:
        return []
    scored = []
    for node in book_tree.nodes(book_id):
        share, shared = score_title(query_tokens, node['title'])
        if shared >= MIN_SHARED or share >= MIN_SHARE:
            scored.append({**node, 'title_share': round(share, 3), 'shared_words': shared})
    scored.sort(key=lambda n: (n['shared_words'], n['title_share']), reverse=True)
    return scored[:limit]


def pages_for(nodes, limit=TREE_PAGES):
    """Physical pages the matched sections cover, nearest the section start first."""
    pages, seen = [], set()
    for node in nodes:
        for page in range(node['page_start'], node['page_end'] + 1):
            if page in seen:
                continue
            seen.add(page)
            pages.append((page, node))
            if len(pages) >= limit:
                return pages
    return pages


def search(query, book_ids=()):
    """Candidate segments from the sections whose titles match, tagged with their provenance."""
    books = list(book_ids) or sorted({s.get('book_id', '') for s in segment_index.load_segments()})
    hits, report = [], []
    for book_id in books:
        if not book_id or not book_tree.load(book_id):
            continue
        nodes = match_nodes(book_id, query)
        if not nodes:
            continue
        for page, node in pages_for(nodes):
            for parent in segment_index.page_parents(book_id, page):
                hits.append({'book_id': book_id, 'page': page, 'text': parent,
                             'section_id': node['id'], 'section': node['title'],
                             'title_share': node['title_share']})
        report.append({'book_id': book_id,
                       'matched_sections': [{'id': n['id'], 'title': n['title'],
                                             'pages': [n['page_start'], n['page_end']],
                                             'shared_words': n['shared_words']} for n in nodes]})
    return hits, report


def segment_hits(chunks, query, book_ids=()):
    """The matched pages expressed as real corpus segments, for the fusion step.

    Returns existing corpus rows, never synthetic text, so everything downstream — parent
    recovery, span numbering, citation pages — behaves exactly as it does for the other two
    routes.
    """
    hits, report = search(query, book_ids)
    if not hits:
        return [], report
    wanted = {(h['book_id'], h['page']): h for h in hits}
    out = []
    for chunk in chunks:
        key = (chunk.get('book_id', ''), int(chunk.get('page_start', 0) or 0))
        hit = wanted.get(key)
        if hit is None:
            continue
        out.append({**chunk, 'tree_section_id': hit['section_id'],
                    'tree_section': hit['section'], 'tree_title_share': hit['title_share']})
    out.sort(key=lambda c: c['tree_title_share'], reverse=True)
    return out, report
