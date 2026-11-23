"""Source-reviewed bibliographic facts, separate from generated religious answers."""
import asyncio, hashlib, json, re
from difflib import SequenceMatcher
from functools import lru_cache
from app.core.config import ROOT, BOOKS
from app.core.language import detect
from app.ingestion.indexer import catalog

METADATA_DIR=ROOT/'data/book-metadata'

def normalized(text):
    return ' '.join(re.findall(r'[^\W_]+',text.lower()))

def identify(question):
    q=question.strip().rstrip('?.!؟').strip()
    patterns={
      'author':[r'who is (?:the )?(?:author|writer)(?: of (.+))?',r'who (?:wrote|authored) (.+)',r'(?:author|writer)(?: name)?(?: of (.+))?',r'(?:is |yeh |ye )?kitab (?:kisne likhi|ka (?:author|musannif) (?:kaun|kon) hai)',r'(?:اس کتاب کا مصنف کون ہے|یہ کتاب کس نے لکھی ہے)',r'(?:इस किताब के लेखक कौन हैं|यह किताब किसने लिखी है)'],
      'publisher':[r'who (?:is (?:the )?publisher of|published) (.+)',r'(?:what is )?(?:the )?publisher(?: of (.+))?'],
      'isbn':[r'(?:what is )?(?:the )?isbn(?: (?:number )?of (.+))?'],
      'first_published':[r'when was (.+) first published',r'(?:first publication|first published)(?: date| year)?(?: of (.+))?'],
      'title':[r'what is (?:the )?(?:title|name) of (.+)'],
    }
    for field,forms in patterns.items():
        for form in forms:
            match=re.fullmatch(form,q,re.I)
            if match: return field,next((x for x in match.groups() if x),None)
    return None,None

def title_matches(mentioned,book,record):
    if not mentioned or normalized(mentioned) in {'this book','the book','my book','uploaded book','is kitab','ye kitab'}: return True
    mentioned=normalized(mentioned)
    return any(SequenceMatcher(None,mentioned,normalized(title)).ratio()>=.82 for title in [book['title'],*record.get('aliases',[])])

@lru_cache(maxsize=16)
def file_hash(path,size,modified):
    return hashlib.sha256(__import__('pathlib').Path(path).read_bytes()).hexdigest()

def read_reviewed(book):
    path=METADATA_DIR/(book['id']+'.json')
    try:
        record=json.loads(path.read_text(encoding='utf-8'))
        source=(BOOKS/book['filename']).resolve()
        if source.parent!=BOOKS.resolve(): return None
        stat=source.stat()
        if record.get('review_status')!='visually_verified' or record.get('pdf_sha256')!=book['hash']: return None
        if file_hash(str(source),stat.st_size,stat.st_mtime_ns)!=record['pdf_sha256']: return None
        return record
    except (OSError,ValueError,KeyError): return None

def lookup(question):
    field,mentioned=identify(question)
    if not field:return None
    candidates=[]
    for book in catalog():
        record=read_reviewed(book)
        if not record or not title_matches(mentioned,book,record):continue
        fact=record.get('facts',{}).get(field)
        if not fact or not isinstance(fact.get('page'),int) or not 1<=fact['page']<=book['pages']:continue
        if not fact.get('quote') or len(fact['quote'].split())>25 or not fact.get('values',{}).get('English'):continue
        candidates.append((book,field,fact))
    # Several books can answer the same field (both books here have the same author). The
    # answer names each book with its own value, so nothing is ambiguous to the reader.
    return candidates or None

FIELD_LABELS={
  'English':{'author':'Author','publisher':'Publisher','isbn':'ISBN','first_published':'First published','title':'Title','editor':'Editor'},
  'Urdu':{'author':'مصنف','publisher':'ناشر','isbn':'ISBN','first_published':'اشاعت اول','title':'عنوان','editor':'مرتب'},
  'Hindi':{'author':'लेखक','publisher':'प्रकाशक','isbn':'ISBN','first_published':'पहला प्रकाशन','title':'शीर्षक','editor':'संपादक'},
  'Hinglish':{'author':'Musannif','publisher':'Publisher','isbn':'ISBN','first_published':'Pehli ishaat','title':'Kitab ka naam','editor':'Murattib'},
}


def display_title(book,language='English',short=True):
    """The reviewed title ("Creation of Man"), not the PDF file name ("creation man 1")."""
    record=read_reviewed(book) or {}
    values=((record.get('facts') or {}).get('title') or {}).get('values') or {}
    title=values.get(language) or values.get('English') or book.get('title','')
    return re.split(r'\s+\(',title)[0].strip() if short else title


def multi_answer(state,result,lang):
    labels=FIELD_LABELS.get(lang,FIELD_LABELS['English'])
    lines,citations=[],[]
    for number,(book,field,fact) in enumerate(result,start=1):
        value=fact['values'].get(lang,fact['values']['English'])
        citations.append({'id':number,'book_id':book['id'],'book_title':display_title(book),'page':fact['page'],
                          'chapter':'Title and publication details','excerpt':fact['quote'],'ocr':False,
                          'transcription_reviewed':True})
        lines.append(f"- **{display_title(book,lang)}** — {labels[field]}: {value} [{number}]")
    answer='\n'.join(lines)
    turn={'question':state['user_input'],'answer':answer,'language':lang,'citations':citations,'grounded':True,
          'coverage':'full','provider_used':'book_metadata','model_used':'','fallback_used':False,'execution':[],
          'reason_code':'','answer_format':'markdown','verification':'reviewed_metadata'}
    return {'bibliography_answered':True,'detected_language':lang,'final_answer':answer,'citations':citations,
            'grounded':True,'provider_used':'book_metadata','reason_code':'','coverage':'full',
            'answer_format':'markdown','verification':'reviewed_metadata',
            'history':(state.get('history',[])+[turn])[-10:]}


async def run(state):
    result=await asyncio.to_thread(lookup,state['user_input'])
    if result is None:
        return await run_reference(state) or {'bibliography_answered':False}
    if isinstance(result,tuple): result=[result]   # a single (book, field, fact)
    # "this book" in a conversation means the book the previous answer was drawn from.
    previous=next((t for t in reversed(state.get('history') or []) if t.get('citations')
                   and t.get('provider_used')!='book_metadata'),None)
    if previous and len(result)>1:
        used={c.get('book_id') for c in previous['citations']}
        narrowed=[r for r in result if r[0]['id'] in used]
        if narrowed: result=narrowed
    lang=detect(state['user_input'],state.get('language_hint','auto'))
    if len(result)>1: return multi_answer(state,result,lang)
    book,field,fact=result[0]
    labels={
      'English':{'author':'Author','publisher':'Publisher','isbn':'ISBN','first_published':'First published','title':'Title'},
      'Urdu':{'author':'مصنف','publisher':'ناشر','isbn':'ISBN','first_published':'اشاعت اول','title':'عنوان'},
      'Hindi':{'author':'लेखक','publisher':'प्रकाशक','isbn':'ISBN','first_published':'पहला प्रकाशन','title':'शीर्षक'},
      'Hinglish':{'author':'Musannif','publisher':'Publisher','isbn':'ISBN','first_published':'Pehli ishaat','title':'Kitab ka naam'},
    }
    value=fact['values'].get(lang,fact['values']['English'])
    citation={'id':1,'book_id':book['id'],'book_title':display_title(book),'page':fact['page'],'chapter':'Title and publication details','excerpt':fact['quote'],'ocr':False,'transcription_reviewed':True}
    answer=f"{labels[lang][field]}: {value}. [1]\n\nSources\n[1] {display_title(book)} · PDF page {fact['page']} — «{fact['quote']}»"
    turn={'question':state['user_input'],'answer':answer,'language':lang,'citations':[citation],'grounded':True,'coverage':'full','provider_used':'book_metadata','model_used':'','fallback_used':False,'execution':[],'reason_code':''}
    return {'bibliography_answered':True,'detected_language':lang,'final_answer':answer,'citations':[citation],'grounded':True,'provider_used':'book_metadata','reason_code':'','coverage':'full','history':(state.get('history',[])+[turn])[-10:]}


# ---------------------------------------------------------------------------------------------
# "Which book is this from? / reference kahan se hai?" (2026-11-16).
# Answers explain the subject directly, without "the book says" in every sentence, so the
# reader needs one place to ask where it all comes from. This returns the reviewed
# bibliographic card (title, author, publisher, first edition, ISBN, each with its page) plus
# the pages the previous answer drew on. No model call.
# ---------------------------------------------------------------------------------------------
REFERENCE_PATTERNS = [
    r'\b(?:kis|kaun\s*si|kon\s*si|konsi|kaunsi|kaun\s*se|kon\s*se)\s+(?:book|kitab|kitaab)\b',
    r'\bwhich book\b',
    r'\b(?:reference|referance|refrence|refernce|source|sources|hawala|hawale|havala|citation|bibliography)\b',
    r'\b(?:where|kahan|kaha|kahaan)\b.{0,25}\b(?:from|se|liya|li|mila|taken)\b',
    r'\b(?:book|kitab|kitaab)\b.{0,12}\b(?:naam|name|title)\b|\b(?:name|title) of (?:the|this) book\b',
    r'کس کتاب|کون سی کتاب|کتاب کا نام|حوالہ|حوالے|ماخذ',
    r'किस किताब|कौन सी किताब|किताब का नाम|स्रोत|हवाला|संदर्भ',
]
# Content questions that merely contain one of those words ("what does the book say about
# references to hadith?") must still go to the explanation path.
CONTENT_SIGNS = re.compile(
    r'\b(?:about|bare|baare|barey|explain|samjha|samjhao|tafseel|detail|regarding|say|likha)\b|'
    r'کے بارے|بارے میں|के बारे', re.I)


REFERENCE_WORDS = {
    'reference', 'referance', 'refrence', 'refernce', 'references', 'source', 'sources', 'hawala',
    'hawale', 'havala', 'citation', 'citations', 'bibliography', 'book', 'books', 'kitab', 'kitaab',
    'naam', 'name', 'title', 'answer', 'jawab', 'jawaab', 'liya', 'li', 'mila', 'taken', 'from',
    'batao', 'bataiye', 'do', 'dijiye', 'give', 'tell', 'show', 'pages', 'page',
    'حوالہ', 'حوالے', 'ماخذ', 'کتاب', 'نام', 'جواب', 'स्रोत', 'हवाला', 'संदर्भ', 'किताब', 'नाम', 'जवाब'}


def is_reference_question(question):
    """Asks where the answer comes from, and nothing else of substance.

    "What was the source of law in Madinah?" contains "source" but asks about law and Madinah,
    so it must go to the explanation path; "source kya hai?" names nothing else.
    """
    from app.retrieval.query_expansion import content_words
    q = question.strip().lower()
    if len(q.split()) > 16 or CONTENT_SIGNS.search(q):
        return False
    if not any(re.search(p, q, re.I) for p in REFERENCE_PATTERNS):
        return False
    return not [w for w in content_words(question) if w.lower() not in REFERENCE_WORDS]


CARD_LABELS = {
    'English': {'heading': 'Book reference', 'title': 'Book', 'author': 'Author', 'editor': 'Editor', 'publisher': 'Publisher',
                'first_published': 'First published', 'isbn': 'ISBN',
                'pages': 'Pages used in the previous answer',
                'note': 'Every [n] in an answer opens the exact PDF page it was taken from.'},
    'Hinglish': {'heading': 'Kitab ka hawala', 'title': 'Kitab', 'author': 'Musannif', 'editor': 'Murattib', 'publisher': 'Publisher',
                 'first_published': 'Pehli ishaat', 'isbn': 'ISBN',
                 'pages': 'Pichhle jawab mein istemal hue safhat',
                 'note': 'Har jawab mein [n] par click karke asal PDF page dekh sakte hain.'},
    'Urdu': {'heading': 'کتاب کا حوالہ', 'title': 'کتاب', 'author': 'مصنف', 'editor': 'مرتب', 'publisher': 'ناشر',
             'first_published': 'اشاعتِ اول', 'isbn': 'ISBN',
             'pages': 'پچھلے جواب میں استعمال ہونے والے صفحات',
             'note': 'ہر جواب میں [n] پر کلک کر کے اصل PDF صفحہ دیکھا جا سکتا ہے۔'},
    'Hindi': {'heading': 'किताब का हवाला', 'title': 'किताब', 'author': 'लेखक', 'editor': 'संपादक', 'publisher': 'प्रकाशक',
              'first_published': 'पहला प्रकाशन', 'isbn': 'ISBN',
              'pages': 'पिछले जवाब में इस्तेमाल हुए पृष्ठ',
              'note': 'हर जवाब में [n] पर क्लिक करके असली PDF पृष्ठ देखा जा सकता है।'},
}


CARD_LEAD = {
    'English': {'yes': 'Yes — this answer was taken from the following book, and every point in it is linked to its page.',
                'always': 'Every answer here is taken only from this book, and every point is linked to its page.',
                'question': 'Your question: “{question}” — answered from these pages:'},
    'Hinglish': {'yes': 'Ji haan — yeh jawab isi kitab se liya gaya hai, aur har baat ke saath uska page diya gaya hai.',
                 'always': 'Yahan har jawab sirf isi kitab se diya jata hai, aur har baat ke saath uska page hota hai.',
                 'question': 'Aapka sawal: “{question}” — iska jawab in safhat se liya gaya:'},
    'Urdu': {'yes': 'جی ہاں — یہ جواب اسی کتاب سے لیا گیا ہے، اور ہر بات کے ساتھ اس کا صفحہ دیا گیا ہے۔',
             'always': 'یہاں ہر جواب صرف اسی کتاب سے دیا جاتا ہے، اور ہر بات کے ساتھ اس کا صفحہ ہوتا ہے۔',
             'question': 'آپ کا سوال: “{question}” — اس کا جواب ان صفحات سے لیا گیا:'},
    'Hindi': {'yes': 'जी हाँ — यह जवाब इसी किताब से लिया गया है, और हर बात के साथ उसका पृष्ठ दिया गया है।',
              'always': 'यहाँ हर जवाब सिर्फ़ इसी किताब से दिया जाता है, और हर बात के साथ उसका पृष्ठ होता है।',
              'question': 'आपका सवाल: “{question}” — इसका जवाब इन पृष्ठों से लिया गया:'},
}


def reference_card(state, lang):
    books = catalog()
    if not books:
        return None
    labels = CARD_LABELS.get(lang, CARD_LABELS['English'])
    lead = CARD_LEAD.get(lang, CARD_LEAD['English'])
    previous = next((t for t in reversed(state.get('history') or [])
                     if t.get('citations') and t.get('provider_used') != 'book_metadata'), None)
    lines, citations = [f"### {labels['heading']}", lead['yes'] if previous else lead['always'], ''], []

    def cite(book, page, excerpt, chapter, reviewed):
        for c in citations:
            if c['book_id'] == book['id'] and c['page'] == page:
                return c['id']
        citations.append({'id': len(citations) + 1, 'book_id': book['id'], 'book_title': display_title(book),
                          'page': page, 'chapter': chapter, 'excerpt': excerpt, 'ocr': not reviewed,
                          'transcription_reviewed': reviewed})
        return len(citations)

    used = {c.get('book_id') for c in (previous or {}).get('citations') or []}
    for book in [b for b in books if not used or b['id'] in used]:
        record = read_reviewed(book) or {}
        facts = record.get('facts', {})
        title_fact = facts.get('title') or {}
        values = title_fact.get('values') or {}
        title = values.get(lang) or values.get('English') or book['title']
        mark = ''
        if isinstance(title_fact.get('page'), int):
            mark = f" [{cite(book, title_fact['page'], title_fact.get('quote', ''), 'Title and publication details', True)}]"
        lines.append(f"**{labels['title']}:** {title}{mark}")
        for field in ('author', 'editor', 'publisher', 'first_published', 'isbn'):
            fact = facts.get(field)
            if not fact or not isinstance(fact.get('page'), int):
                continue
            value = (fact.get('values') or {}).get(lang) or (fact.get('values') or {}).get('English')
            if not value:
                continue
            number = cite(book, fact['page'], fact.get('quote', ''), 'Title and publication details', True)
            lines.append(f"- **{labels[field]}:** {value} [{number}]")
    if previous:
        lines.append('')
        lines.append(f"### {labels['pages']}")
        asked = str(previous.get('question', '')).strip()
        if asked:
            lines.append(lead['question'].format(question=asked[:160]))
        by_id = {b['id']: b for b in books}
        for old in previous['citations']:
            book = by_id.get(old.get('book_id'))
            if not book:
                continue
            number = cite(book, old['page'], old.get('excerpt', ''), old.get('chapter', ''), False)
            section = f" — ⁨{old['chapter']}⁩" if old.get('chapter') else ''
            lines.append(f"- PDF page {old['page']}{section} [{number}]")
    lines.append('')
    lines.append(f"> {labels['note']}")
    return '\n'.join(lines), citations


async def run_reference(state):
    if not is_reference_question(state['user_input']):
        return None
    lang = detect(state['user_input'], state.get('language_hint', 'auto'))
    card = await asyncio.to_thread(reference_card, state, lang)
    if not card:
        return None
    answer, citations = card
    turn = {'question': state['user_input'], 'answer': answer, 'language': lang, 'citations': citations,
            'grounded': True, 'coverage': 'full', 'provider_used': 'book_metadata', 'model_used': '', 'fallback_used': False,
            'execution': [], 'reason_code': '', 'answer_format': 'markdown', 'verification': 'reviewed_metadata'}
    return {'bibliography_answered': True, 'detected_language': lang, 'final_answer': answer,
            'citations': citations, 'grounded': True, 'provider_used': 'book_metadata', 'reason_code': '',
            'coverage': 'full', 'answer_format': 'markdown', 'verification': 'reviewed_metadata',
            'history': (state.get('history', []) + [turn])[-10:]}
