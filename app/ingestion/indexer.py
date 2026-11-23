import asyncio,hashlib,json,time
from app.core.config import INDEX,BOOKS,settings
from app.ingestion.pdf_loader import load_pages
from app.ingestion.chunker import chunks_for_page
from app.ingestion.graph_builder import build_graph
from app.retrieval.vector_store import ChromaStore,embed
LOCK=asyncio.Lock()
STATUS={'running':False,'stage':'Not indexed yet','pages_done':0,'report':None,'error':None}
def read_json(name,default):
    p=INDEX/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
def save_json(name,data):
    # Retried: the external D: drive intermittently refuses a write (OSError Errno 22, measured
    # 2026-11-16). The write stays atomic (tmp file + replace); after the retries it raises.
    import time
    path=INDEX/name;tmp=path.with_suffix('.tmp');payload=json.dumps(data,ensure_ascii=False)
    for attempt in range(5):
        try:
            tmp.write_text(payload,encoding='utf-8');tmp.replace(path);return
        except OSError:
            if attempt==4: raise
            time.sleep(.5*(attempt+1))
def catalog(): return read_json('catalog.json',[])
def all_chunks(): return read_json('chunks.json',[])
def get_page(book_id,page):
    return next((p for p in read_json(f'pages-{book_id}.json',[]) if p['page']==page),None)
async def ingest(force=False):
    if LOCK.locked(): return {'status':'already_running'}
    async with LOCK:
        STATUS.update(running=True,stage='Reading PDFs',pages_done=0,error=None)
        report={'pages':0,'chunks':0,'ocr_pages':0,'skipped':0,'warnings':[],'seconds':0};started=time.monotonic()
        try:
            books=catalog();chunks=all_chunks();store=await asyncio.to_thread(ChromaStore)
            for path in BOOKS.glob('*.pdf'):
                digest=hashlib.sha256(path.read_bytes()).hexdigest();book_id=hashlib.sha256(path.name.encode()).hexdigest()[:16]
                old=next((b for b in books if b['id']==book_id),None)
                _emb_tag = settings.gemini_embedding_model if settings.embedding_provider == 'gemini' else settings.embedding_model
                if not force and old and old['hash']==digest and old.get('embedding_model')==_emb_tag and old.get('complete'):
                    report['skipped']+=1;continue
                book={'id':book_id,'title':path.stem.replace('_',' ').replace('-',' '),'filename':path.name,'hash':digest,'embedding_model':_emb_tag,'complete':False}
                import pymupdf
                with pymupdf.open(path) as doc: total_pages=len(doc)
                book.update(pages=total_pages,chunks=0,ocr_pages=0,indexed=False,processed_pages=0)
                books=[b for b in books if b['id']!=book_id]+[book]
                save_json('catalog.json',books)
                pages=[];new=[];batch=[];cleared=False
                async def publish():
                    nonlocal chunks,batch,cleared
                    if not batch: return
                    STATUS['stage']=f"Embedding through page {len(pages)} / {total_pages}"
                    vectors=[]
                    from app.core import resources
                    for start in range(0,len(batch),8):
                        while resources.interactive_count: await asyncio.sleep(.2)
                        vectors.extend(await embed([c['text'] for c in batch[start:start+8]],persist=True))
                    if not cleared:
                        await asyncio.to_thread(store.delete_book,book_id)
                        chunks=[c for c in chunks if c['book_id']!=book_id];cleared=True
                    for start in range(0,len(batch),64): await asyncio.to_thread(store.upsert,batch[start:start+64],vectors[start:start+64])
                    chunks+=batch;batch=[]
                    book.update(chunks=len(new),ocr_pages=sum(p['ocr'] for p in pages),indexed=True,processed_pages=len(pages))
                    save_json(f'pages-{book_id}.json',pages);save_json('chunks.json',chunks);save_json('catalog.json',books)
                iterator=iter(load_pages(path))
                def next_page(): return next(iterator,None)
                while True:
                    p=await asyncio.to_thread(next_page)
                    if p is None: break
                    STATUS.update(stage=f"Reading page {p['page']} / {total_pages}",pages_done=p['page'])
                    pages.append(p)
                    if p['warning']: report['warnings'].append({'book':path.name,'page':p['page'],'message':p['warning']})
                    if sum(c.isalpha() for c in p['text'])>=40:
                        page_chunks=list(chunks_for_page(p,book));new+=page_chunks;batch+=page_chunks
                    if len(pages)%32==0: await publish()
                await publish()
                book.update(complete=True,quality_warnings=sum(bool(p['warning']) for p in pages),processed_pages=len(pages))
                save_json(f'pages-{book_id}.json',pages);save_json('catalog.json',books)
                report['pages']+=len(pages);report['chunks']+=len(new);report['ocr_pages']+=book['ocr_pages']
            if settings.enable_knowledge_graph: await asyncio.to_thread(build_graph,chunks)
            report['seconds']=round(time.monotonic()-started,1);save_json('ingestion-report.json',report)
            STATUS.update(stage='Ready' if chunks else 'OCR required — no readable passages',report=report)
            return report
        except Exception as exc:
            STATUS.update(error=str(exc),stage='Indexing failed');raise
        finally: STATUS['running']=False
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');args=parser.parse_args()
    print(json.dumps(asyncio.run(ingest(args.force)),ensure_ascii=False,indent=2))
