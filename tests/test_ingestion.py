import pymupdf
from app.ingestion.chunker import chunks_for_page
from app.ingestion.pdf_loader import readable,load_pages
def test_page_metadata():
    chunks=list(chunks_for_page({'text':'First heading\n'+('A meaningful sentence about history. '*300),'page':17},{'id':'b','title':'Book'}))
    assert len(chunks)>1
    assert all(c['page_start']==c['page_end']==17 and c['book_id']=='b' for c in chunks)
def test_legacy_font_rejected(): assert not readable('Ð gz — ZZ ã Ã ]. Z: H Y e '+('Ãgz ¾ Z W A '*50))
def test_pdf_fixture(tmp_path):
    p=tmp_path/'tiny.pdf';d=pymupdf.open();page=d.new_page();page.insert_text((40,70),'This is a small history book about a city and its people. '*3);d.save(p);d.close()
    pages=list(load_pages(p));assert pages[0]['page']==1;assert 'history' in pages[0]['text']
