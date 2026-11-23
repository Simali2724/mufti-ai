"""Photo / file input (loop 8, 2026-11-18): local text extraction and the no-model page finder."""
import io
import shutil
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import routes_attach
from app.core import extract as ex


def client():
    app = FastAPI()
    app.include_router(routes_attach.router)
    return TestClient(app)


def test_text_file_is_read():
    r = client().post('/extract', files={'file': ('note.txt', 'Misaq-e-Madina kya tha?'.encode('utf-8'), 'text/plain')})
    assert r.status_code == 200 and r.json()['text'] == 'Misaq-e-Madina kya tha?' and r.json()['ocr'] is False


def test_pdf_text_layer_is_read():
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), 'The Charter of Madinah established a written constitution for the city.')
    r = client().post('/extract', files={'file': ('page.pdf', doc.tobytes(), 'application/pdf')})
    assert r.status_code == 200 and 'Charter of Madinah' in r.json()['text'] and r.json()['kind'] == 'pdf'


def _has_tesseract():
    try:
        ex._tesseract()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_tesseract(), reason='Tesseract OCR not installed')
def test_photo_is_read_with_local_ocr():
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1200, 260), 'white')
    ImageDraw.Draw(image).text((40, 90), 'The Charter of Madinah', fill='black', font=ImageFont.load_default(size=56))
    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    r = client().post('/extract', files={'file': ('photo.png', buffer.getvalue(), 'image/png')})
    assert r.status_code == 200 and 'Charter of Madinah' in r.json()['text'] and r.json()['ocr'] is True


@pytest.mark.parametrize('name,data,message', [
    ('virus.exe', b'MZ...', 'Unsupported file'),
    ('empty.txt', b'', 'empty'),
    ('broken.png', b'not an image', 'could not be opened'),
])
def test_bad_files_are_refused_with_a_reason(name, data, message):
    r = client().post('/extract', files={'file': (name, data, 'application/octet-stream')})
    assert r.status_code == 422 and message in r.json()['detail']


def test_oversized_file_is_refused(monkeypatch):
    monkeypatch.setattr(ex, 'MAX_BYTES', 10)
    with pytest.raises(ex.ExtractError):
        ex.extract('a.txt', b'x' * 11)


def test_find_returns_pages_without_any_model(monkeypatch):
    import app.retrieval.hybrid as hybrid
    import app.retrieval.evidence as evidence
    from app.llm import router

    async def fake_search(queries, limit=None, scope=None):
        return ['candidates'], {}
    windows = [{'book_id': 'b', 'book_title': 'Book', 'page_start': 257, 'text': 'Article 27 bars gender discrimination.',
                'relevance': .9, 'lexical_score': .8, 'dense_score': .7},
               {'book_id': 'b', 'book_title': 'Book', 'page_start': 257, 'text': 'same page again', 'relevance': .8},
               {'book_id': 'b', 'book_title': 'Book', 'page_start': 14, 'text': 'contents', 'relevance': .3,
                'lexical_score': .3, 'dense_score': .4}]
    monkeypatch.setattr(hybrid, 'search', fake_search)
    monkeypatch.setattr(evidence, 'select', lambda c, **k: (windows, {}))
    monkeypatch.setattr(router, 'get_chat_model', lambda task: (_ for _ in ()).throw(AssertionError('no model')))
    r = client().post('/find', json={'text': 'gender discrimination in adult franchise'})
    hits = r.json()['results']
    assert r.status_code == 200 and [h['page'] for h in hits] == [257, 14]         # one entry per page
    assert hits[0]['strength'] == 'strong' and hits[1]['strength'] == 'possible'
