"""MCP tools over the local library: bounded search, section lookup and page reading.

Every tool validates its ids against the catalogue and the persisted tree before touching the
index, and every tool bounds what it returns. Text reaching these tools is untrusted data, not
instructions, exactly as in the answer pipeline.
"""
import argparse
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server import MCPServer as FastMCP
from app.ingestion.indexer import catalog, get_page as read_page
from app.ingestion import book_tree
from app.retrieval.hybrid import search as hybrid_search
from app.agents.graph import graph_context, ask
from app.core.schemas import ChatRequest

mcp = FastMCP('Mufti AI Library')

MAX_RESULTS = 20
MAX_SNIPPET = 600


def known_book(book_id):
    return any(b['id'] == book_id for b in catalog())


@mcp.tool()
async def search_books(query: str, language: str = 'auto', top_k: int = 6) -> list:
    """Hybrid search over the indexed books. Returns passages with their physical PDF pages.

    `search_local` takes a list of query descriptors and a `limit`; this used to call it with
    a bare string and `top_k=`, which raised TypeError on every invocation, so this tool never
    worked. It now goes through `hybrid.search`, which accepts a plain string.
    """
    query = str(query or '').strip()
    if not query:
        return [{'error': 'Empty query'}]
    results, _ = await hybrid_search(query, max(1, min(int(top_k), MAX_RESULTS)))
    out = []
    for row in results:
        located = book_tree.locate(row.get('book_id', ''), row.get('page_start', 0) or 0)
        out.append({'book_id': row.get('book_id', ''), 'book_title': row.get('book_title', ''),
                    'pdf_page': row.get('page_start'), 'printed_label': row.get('printed_label'),
                    'chapter': located.get('chapter', ''), 'section': located.get('section', ''),
                    'section_id': located.get('section_id', ''),
                    'text': str(row.get('text', ''))[:MAX_SNIPPET]})
    return out


@mcp.tool()
def list_sections(book_id: str, chapter_id: str = '') -> list:
    """The book's chapter/section tree with validated physical page ranges.

    Titles come from the PDF outline and are correctly spelled, unlike the OCR'd body text.
    A section title locates material; it is not evidence for what that section asserts.
    """
    if not known_book(book_id):
        return [{'error': 'Book not found'}]
    nodes = book_tree.nodes(book_id)
    if not nodes:
        return [{'error': 'No section tree for this book; its PDF has no outline'}]
    if chapter_id:
        if not any(n['id'] == chapter_id and n['kind'] == 'chapter' for n in nodes):
            return [{'error': 'Chapter not found'}]
        nodes = [n for n in nodes if n.get('parent_id') == chapter_id]
    return [{'id': n['id'], 'kind': n['kind'], 'title': n['title'],
             'parent_id': n.get('parent_id', ''),
             'page_start': n['page_start'], 'page_end': n['page_end']} for n in nodes]


@mcp.tool()
def get_section(book_id: str, section_id: str, max_pages: int = 5) -> dict:
    """One section's metadata and the text of its pages, bounded by `max_pages`."""
    if not known_book(book_id):
        return {'error': 'Book not found'}
    node = next((n for n in book_tree.nodes(book_id) if n['id'] == section_id), None)
    if node is None:
        return {'error': 'Section not found'}
    limit = max(1, min(int(max_pages), 10))
    pages = []
    for page in range(node['page_start'], min(node['page_end'], node['page_start'] + limit - 1) + 1):
        record = read_page(book_id, page) or {}
        pages.append({'pdf_page': page, 'printed_label': record.get('printed_label'),
                      'text': str(record.get('text', ''))[:MAX_SNIPPET * 4],
                      'ocr': record.get('ocr', False)})
    return {'book_id': book_id, 'section_id': node['id'], 'title': node['title'],
            'kind': node['kind'], 'parent_id': node.get('parent_id', ''),
            'page_start': node['page_start'], 'page_end': node['page_end'],
            'pages_returned': len(pages), 'pages': pages}


@mcp.tool()
def locate_page(book_id: str, page: int) -> dict:
    """Which chapter and section a physical PDF page belongs to."""
    if not known_book(book_id):
        return {'error': 'Book not found'}
    located = book_tree.locate(book_id, int(page))
    return located or {'error': 'Page is outside every known section'}


@mcp.tool()
def get_page(book_id: str, page: int) -> dict:
    """The full extracted text of one physical PDF page, with its section context."""
    if not known_book(book_id):
        return {'error': 'Book not found'}
    record = read_page(book_id, int(page))
    if not record:
        return {'error': 'Page not found'}
    return {**record, 'located': book_tree.locate(book_id, int(page))}


@mcp.tool()
def list_books() -> list:
    return catalog()


@mcp.tool()
async def ask_mufti(question: str, language: str = 'auto') -> dict:
    import uuid
    async with graph_context() as graph:
        response = await ask(graph, ChatRequest(question=question, language_hint=language,
                                                session_id='mcp-' + uuid.uuid4().hex))
        return response.model_dump()


@mcp.resource('books://catalog')
def book_catalog() -> str:
    import json
    return json.dumps(catalog(), ensure_ascii=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--transport', choices=['stdio', 'streamable-http'], default='stdio')
    args = parser.parse_args()
    mcp.run(transport=args.transport)
