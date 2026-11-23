import asyncio
from fastapi import APIRouter,BackgroundTasks,HTTPException
from fastapi.responses import FileResponse
from app.core.config import settings,BOOKS,INDEX,config
from app.ingestion.indexer import catalog,get_page,ingest,STATUS,read_json
router=APIRouter()
@router.get('/health')
async def health():
    from app.core.storage import storage_status
    storage=await asyncio.to_thread(storage_status,INDEX)
    from app.core.warmup import STATE as warmup
    return {'status':'ok' if storage=='ok' else 'degraded','storage':storage,'books':len(catalog()),'index':STATUS,'warmup':warmup,'embedding_model':settings.embedding_model,'chat_model':settings.ollama_chat_model,'report':read_json('ingestion-report.json',{})}

@router.get('/health/setup')
async def setup():
    """New-user setup checklist with fixes in English and Hinglish (app/core/setup_check.py)."""
    from app.core.setup_check import run_checks
    return await run_checks()

@router.get('/books/{book_id}/outline')
async def outline(book_id:str):
    """Chapters and sections with physical PDF page ranges, for the chapter explorer."""
    from app.agents.bibliography import display_title
    from app.agents.suggest import outline as book_outline
    book=next((b for b in catalog() if b['id']==book_id),None)
    if not book: raise HTTPException(404,'Book not found')
    return {'book_id':book_id,'title':display_title(book),'chapters':book_outline(book_id)}

@router.get('/topics')
async def topics():
    """Topic index: reviewed key concepts + every chapter/section with page ranges (no model call)."""
    from app.agents.suggest import topic_index
    return topic_index()

@router.get('/suggestions')
async def suggestions(language:str='Hinglish'):
    """Starter questions built from the books' own chapter titles (no model call)."""
    from app.agents.suggest import starter_topics
    if language not in ('English','Hinglish','Urdu','Hindi'): language='Hinglish'
    return {'language':language,'questions':starter_topics(language,limit=6)}
@router.get('/books')
async def books():
    from app.agents.bibliography import display_title
    out=[]
    for book in catalog():
        out.append({**book,'display_title':display_title(book),'language':book_language(book['id'])})
    return out
_languages={}
def book_language(book_id):
    """Main script of a book's text, for the library card ("Urdu" / "English")."""
    if book_id not in _languages:
        text=' '.join(p.get('text','') for p in read_json(f'pages-{book_id}.json',[])[:40])
        arabic=sum('\u0600'<=c<='\u06ff' for c in text);latin=sum(c.isascii() and c.isalpha() for c in text)
        _languages[book_id]='Urdu' if arabic>latin*.5 else 'English'
    return _languages[book_id]
@router.get('/books/{book_id}/pages/{page}')
async def page(book_id:str,page:int):
    if not any(b['id']==book_id for b in catalog()): raise HTTPException(404,'Book not found')
    result=get_page(book_id,page)
    if result is None: raise HTTPException(404,'Page not found')
    # Raw OCR, any reviewed correction and the printed page label stay separate facts.
    from app.ingestion.segments import corrections_for,printed_label,quality
    correction=corrections_for(book_id).get(page)
    return {**result,'raw_text':result.get('text',''),
            'corrected_text':correction['corrected_text'] if correction else '',
            'correction_source':correction.get('source','') if correction else '',
            'correction_reviewer':correction.get('reviewer','') if correction else '',
            'printed_label':printed_label(result.get('text','')),
            'extraction_quality':quality(result.get('text',''))}

@router.get('/books/{book_id}/extraction-audit')
async def extraction_audit(book_id:str,limit:int=100):
    rows=[r for r in read_json('extraction-audit.json',[]) if r.get('book_id')==book_id]
    flagged=[r for r in rows if r['flags']]
    return {'pages':len(rows),'flagged':len(flagged),
            'by_flag':{f:sum(1 for r in rows if f in r['flags']) for f in sorted({f for r in rows for f in r['flags']})},
            'worst':sorted(flagged,key=lambda r:r['score'])[:limit]}
@router.get('/books/{book_id}/pdf')
async def pdf(book_id:str):
    b=next((b for b in catalog() if b['id']==book_id),None)
    if not b: raise HTTPException(404,'Book not found')
    path=(BOOKS/b['filename']).resolve()
    if path.parent!=BOOKS.resolve(): raise HTTPException(400,'Invalid filename')
    return FileResponse(path,media_type='application/pdf')
async def ingest_safe(force=False):
    try: await ingest(force)
    except Exception:
        from app.core.logging import logger
        logger.exception('Library ingestion failed')
@router.post('/ingest',status_code=202)
async def reindex(background:BackgroundTasks,force:bool=False):
    if STATUS['running']: return {'status':'already_running'}
    background.add_task(ingest_safe,force);return {'status':'started'}
@router.get('/health/providers')
async def providers():
    import httpx
    async def ping(p):
        key=getattr(settings,{'openai':'openai_api_key','anthropic':'anthropic_api_key','gemini':'google_api_key'}.get(p,'openai_api_key'))
        if p!='ollama' and not key: return p,{'status':'not_configured'}
        try:
            async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
                if p=='ollama': r=await client.get(settings.ollama_base_url+'/api/tags')
                elif p=='openai': r=await client.get('https://api.openai.com/v1/models',headers={'Authorization':'Bearer '+key})
                elif p=='anthropic': r=await client.get('https://api.anthropic.com/v1/models',headers={'x-api-key':key,'anthropic-version':'2023-06-01'})
                else: r=await client.get('https://generativelanguage.googleapis.com/v1beta/models',headers={'x-goog-api-key':key})
                r.raise_for_status();return p,{'status':'online',**({'models':[m['name'] for m in r.json()['models']]} if p=='ollama' else {})}
        except Exception as e: return p,{'status':'offline','error':type(e).__name__}
    return dict(await asyncio.gather(*(ping(p) for p in ['ollama','openai','gemini','anthropic'])))
