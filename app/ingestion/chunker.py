import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import config
def chunks_for_page(page,book):
    splitter=RecursiveCharacterTextSplitter(chunk_size=config['chunk_size'],chunk_overlap=config['chunk_overlap'],separators=['\n\n','\n','۔','。','. ',' ',''])
    heading=next((line.strip()[:150] for line in page['text'].splitlines()[:15] if re.match(r'^(?:باب|فصل|مبحث|chapter)\b',line.strip(),re.I)),'')
    for i,text in enumerate(splitter.split_text(page['text'])):
        yield {'id':f"{book['id']}-{page['page']}-{i}",'text':text,'book_id':book['id'],'book_title':book['title'],'page_start':page['page'],'page_end':page['page'],'chapter':heading,'language':'Urdu','ocr':page.get('ocr',False)}
