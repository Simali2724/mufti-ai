import pymupdf as fitz
import json,hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from app.core.config import INDEX
from app.ingestion.ocr import ocr_page
def readable(text):
    letters=[c for c in text if c.isalpha()]
    arabic=sum('\u0600'<=c<='\u06ff' for c in letters)
    # Legacy InPage fonts can expose hundreds of meaningless Latin glyphs.
    latin=sum(c.isascii() for c in letters)
    words=text.split()
    return len(letters)>=40 and (arabic/max(1,len(letters))>.3 or (latin/max(1,len(letters))>.93 and sum(len(w)>3 for w in words)/max(1,len(words))>.4)) and text.count('�')<5
def process_page(args):
    path,i,cache_path=args
    cached=Path(cache_path)/f'{i+1}.json'
    if cached.exists():
        result=json.loads(cached.read_text(encoding='utf-8'))
        if not result.get('warning'): return result
    with fitz.open(path) as doc:
        page=doc[i]
        text=page.get_text('text',sort=True).strip();used_ocr=False;warning=''
        if not readable(text):
            try: text=ocr_page(page).strip();used_ocr=True
            except Exception as exc: warning=str(exc)
        if not readable(text): warning=warning or 'Very little readable text; inspect original page'
        result={'page':i+1,'text':text if readable(text) else '', 'ocr':used_ocr,'warning':warning}
        cached.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        return result
def load_pages(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    from app.core.config import ROOT
    engine='nastaliq-masked-v1' if (ROOT/'data/tessdata/urd_naw.traineddata').exists() else 'standard-v1'
    cache=INDEX/'ocr-cache'/(digest+'-'+engine)
    cache.mkdir(parents=True,exist_ok=True)
    with fitz.open(path) as doc:
        count=len(doc)
    # PyMuPDF is not thread-safe: each worker owns its document and native state.
    with ProcessPoolExecutor(max_workers=2) as pool:
        yield from pool.map(process_page,((str(path),i,str(cache)) for i in range(count)))
