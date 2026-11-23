import re,unicodedata
def normalize(text):
    text=unicodedata.normalize('NFKC',text).replace('ـ','')
    text=text.translate(str.maketrans({'ي':'ی','ك':'ک','ى':'ی','أ':'ا','إ':'ا','آ':'ا'}))
    return re.sub(r'[\u064b-\u065f\u0670]','',text)
def tokens(text): return re.findall(r'[^\W_]+',normalize(text).lower())
