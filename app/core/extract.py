"""Text from a photo or a file the reader gives us (loop 8, 2026-11-18).

Photos (camera or folder), PDFs, .txt and .md files become plain text ON THIS COMPUTER:
  * images -> Tesseract OCR (Urdu / Arabic / English / Hindi traineddata in data/tessdata),
    after EXIF rotation, greyscale, contrast and upscaling of small photos;
  * PDFs   -> the PDF's own text layer (first MAX_PDF_PAGES pages), OCR for pages without one;
  * text   -> decoded as UTF-8.
Nothing is sent to a cloud service and nothing is stored: the bytes live only in this request.
The text is then used by the normal, grounded pipeline ("Explain this") or by the no-model page
finder (POST /find) — the books remain the only source of any answer.
"""
import io
import os
import re
import shutil
import time
from pathlib import Path
from app.core.config import ROOT

MAX_BYTES = 15 * 1024 * 1024
MAX_PDF_PAGES = 5
MAX_CHARS = 6000
# Urdu uses the Nastaliq model: measured 2026-11-18 on scanned book pages 257 / 51, urd_naw read
# 72 / 86 Urdu words vs 40 / 58 (urd) and 38 / 52 (urd-best). Unavailable models are dropped at run time.
OCR_LANGS = {'auto': 'urd_naw+eng', 'Urdu': 'urd_naw+eng', 'Arabic': 'ara+eng', 'English': 'eng', 'Hindi': 'hin+eng'}
IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff', '.gif'}
TEXT_TYPES = {'.txt', '.md'}


class ExtractError(ValueError):
    pass


def _tesseract():
    import pytesseract
    if (ROOT / 'data/tessdata/urd.traineddata').exists():
        os.environ['TESSDATA_PREFIX'] = str(ROOT / 'data/tessdata')
    binary = shutil.which('tesseract') or next(
        (str(p) for p in [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Tesseract-OCR/tesseract.exe']
         if p.exists()), '')
    if not binary:
        raise ExtractError('Tesseract OCR is not installed, so text cannot be read from photos. See README → OCR.')
    pytesseract.pytesseract.tesseract_cmd = binary
    os.environ.setdefault('OMP_THREAD_LIMIT', '2')
    return pytesseract


def prepare(image):
    """Phone photos: honour EXIF rotation, greyscale, stretch contrast, upscale small images."""
    from PIL import ImageOps
    image = ImageOps.exif_transpose(image).convert('L')
    image = ImageOps.autocontrast(image, cutoff=1)
    if image.width < 1400:
        factor = 1400 / max(1, image.width)
        image = image.resize((int(image.width * factor), int(image.height * factor)))
    return image


def ocr_image(image, language='auto'):
    pytesseract = _tesseract()
    lang = OCR_LANGS.get(language, OCR_LANGS['auto'])
    available = set(pytesseract.get_languages(config=''))
    lang = '+'.join(l for l in lang.split('+') if l in available) or 'eng'
    text = pytesseract.image_to_string(prepare(image), lang=lang, config='--psm 3')
    # Auto mode: a page with almost no Urdu-script result is retried as English only (an English
    # page read with the Urdu model produces fragments).
    if language == 'auto' and letters(text) < 25 and 'eng' in available:
        english = pytesseract.image_to_string(prepare(image), lang='eng', config='--psm 3')
        if letters(english) > letters(text):
            text = english
    return text


def letters(text):
    return sum(ch.isalpha() for ch in text or '')


def clean(text):
    text = re.sub(r'[ \t]+', ' ', text or '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return '\n'.join(line.strip() for line in text.splitlines()).strip()


def script_of(text):
    counts = {'Urdu/Arabic': len(re.findall(r'[؀-ۿ]', text)), 'Hindi': len(re.findall(r'[ऀ-ॿ]', text)),
              'English': len(re.findall(r'[A-Za-z]', text))}
    best = max(counts, key=counts.get)
    return best if counts[best] else ''


def extract(filename, data, language='auto'):
    """Returns {'text','kind','pages','ocr','chars','truncated','script','seconds'}."""
    started = time.monotonic()
    if not data:
        raise ExtractError('The file is empty.')
    if len(data) > MAX_BYTES:
        raise ExtractError('The file is larger than 15 MB.')
    suffix = Path(filename or '').suffix.lower()
    pages, used_ocr = 1, False
    if suffix in IMAGE_TYPES:
        from PIL import Image, UnidentifiedImageError
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except (UnidentifiedImageError, OSError):
            raise ExtractError('This image could not be opened. Try a JPG or PNG photo.')
        text, kind, used_ocr = ocr_image(image, language), 'image', True
    elif suffix == '.pdf':
        import fitz
        try:
            document = fitz.open(stream=data, filetype='pdf')
        except Exception:
            raise ExtractError('This PDF could not be opened.')
        parts = []
        pages = min(document.page_count, MAX_PDF_PAGES)
        for number in range(pages):
            page = document[number]
            layer = page.get_text().strip()
            if letters(layer) >= 40:
                parts.append(layer)
            else:                                  # scanned page: OCR it
                from PIL import Image
                pix = page.get_pixmap(dpi=220)
                parts.append(ocr_image(Image.frombytes('RGB', [pix.width, pix.height], pix.samples), language))
                used_ocr = True
        text, kind = '\n\n'.join(parts), 'pdf'
    elif suffix in TEXT_TYPES:
        text, kind = data.decode('utf-8', errors='replace'), 'text'
    else:
        raise ExtractError('Unsupported file. Use a photo (JPG/PNG), a PDF, or a .txt/.md file.')
    text = clean(text)
    if letters(text) < 3:
        raise ExtractError('No readable text was found. Try a sharper, well-lit photo of the text, held straight.')
    truncated = len(text) > MAX_CHARS
    text = text[:MAX_CHARS]
    return {'text': text, 'kind': kind, 'pages': pages, 'ocr': used_ocr, 'chars': len(text),
            'truncated': truncated, 'script': script_of(text), 'seconds': round(time.monotonic() - started, 2)}
