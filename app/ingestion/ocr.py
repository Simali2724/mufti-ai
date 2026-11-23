import os,shutil
from pathlib import Path
def ocr_page(page):
    import pytesseract
    from PIL import Image,ImageDraw
    from app.core.config import ROOT
    os.environ.setdefault('OMP_THREAD_LIMIT','1')
    if (ROOT/'data/tessdata/urd.traineddata').exists(): os.environ['TESSDATA_PREFIX']=str(ROOT/'data/tessdata')
    binary=shutil.which('tesseract')
    if not binary:
        for p in [Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tesseract-OCR/tesseract.exe',Path('C:/Program Files/Tesseract-OCR/tesseract.exe')]:
            if p.exists(): binary=str(p); break
    if not binary: raise RuntimeError('Tesseract OCR not installed; scanned pages cannot be indexed')
    pytesseract.pytesseract.tesseract_cmd=binary
    langs=pytesseract.get_languages(config='')
    if 'urd' not in langs: raise RuntimeError('Urdu OCR language pack (urd.traineddata) missing')
    pix=page.get_pixmap(dpi=250)
    image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    # Legacy Urdu fonts need script-specific OCR. Preserve valid Latin text directly from PDF.
    english=[]
    if 'urd_naw' in langs:
        draw=ImageDraw.Draw(image);scale=250/72
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    text=span['text'].strip();letters=[c for c in text if c.isalpha()]
                    legacy=any(x in span['font'].upper() for x in ['NOORI','NAFEES'])
                    if not legacy and letters and sum(c.isascii() for c in letters)/len(letters)>.95:
                        draw.rectangle(tuple(v*scale for v in span['bbox']),fill='white');english.append(text)
        text=pytesseract.image_to_string(image,lang='urd_naw',config='--psm 3')
        return text+('\n\nEnglish text on this page:\n'+' '.join(english) if english else '')
    return pytesseract.image_to_string(image,lang='urd-best+eng' if 'urd-best' in langs else 'urd+eng',config='--psm 3')
