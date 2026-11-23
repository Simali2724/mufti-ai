"""Photo / file input (loop 8, 2026-11-18).

POST /extract  multipart {file, language}  -> text read locally from a photo, PDF or text file.
POST /find     {text}                      -> where in the reader's books this passage (or topic)
                                              appears: book, PDF page, excerpt. NO model call — it is
                                              the same hybrid search the answer pipeline uses.
"""
import asyncio
import re
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from app.core.extract import ExtractError, MAX_BYTES, extract

router = APIRouter()


@router.post('/extract')
async def extract_text(file: UploadFile = File(...), language: str = Form('auto')):
    data = await file.read(MAX_BYTES + 1)
    try:
        return await asyncio.to_thread(extract, file.filename or '', data, language)
    except ExtractError as exc:
        raise HTTPException(422, str(exc))


class FindIn(BaseModel):
    text: str = Field(min_length=2, max_length=6000)
    limit: int = Field(default=5, ge=1, le=10)


WORD = re.compile(r'\w+', re.U)


def strength(window, top=0.0):
    """strong only when the absolute scores are high AND the page is close to the best match."""
    lexical, dense = window.get('lexical_score', 0) or 0, window.get('dense_score', 0) or 0
    if (lexical >= .5 or dense >= .62) and (window.get('relevance', 0) or 0) >= .85 * top:
        return 'strong'
    if lexical >= .25 or dense >= .5:
        return 'possible'
    return 'weak'


def excerpt_for(window, query):
    from app.retrieval.evidence import legible_pieces, display_quote
    words = {w.lower() for w in WORD.findall(query) if len(w) > 2}
    pieces = legible_pieces(window.get('text', '')) or [window.get('text', '')]
    best = max(pieces, key=lambda p: len(words & {w.lower() for w in WORD.findall(p)}))
    return display_quote(best, 45)


@router.post('/find')
async def find(body: FindIn):
    from app.retrieval.query_expansion import expand_query, search_queries
    from app.retrieval.hybrid import search
    from app.retrieval.evidence import select
    from app.agents.explain_agent import book_display_title
    query = ' '.join(body.text.split())[:700]           # a long passage: its opening is enough to locate it
    canonical, variants, _concepts = expand_query(query)
    try:
        candidates, _report = await search(search_queries(canonical, variants))
    except Exception as exc:
        raise HTTPException(503, 'The book search is unavailable (is Ollama running?): ' + type(exc).__name__)
    windows, _ = select(candidates, max_windows=body.limit * 2)
    results, seen = [], set()
    top = max((w.get('relevance', 0) or 0 for w in windows), default=0)
    for window in windows:
        key = (window.get('book_id'), window['page_start'])
        if key in seen:
            continue
        seen.add(key)
        results.append({'book_id': window['book_id'],
                        'book_title': book_display_title(window['book_id'], window.get('book_title', '')),
                        'page': window['page_start'], 'printed_label': window.get('printed_label'),
                        'chapter': window.get('chapter', ''), 'excerpt': excerpt_for(window, query),
                        'strength': strength(window, top), 'relevance': window.get('relevance', 0)})
        if len(results) >= body.limit:
            break
    return {'query': query[:200], 'results': results}
