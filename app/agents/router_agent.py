"""Intent routing with a deterministic fast path for obvious book questions.

A question that clearly asks about the indexed book does not need a model call to be
classified. The deterministic path is measured against the model router in the benchmark
(eval/run_benchmark.py --router) before it is trusted; anything it is unsure about still
goes to the model.
"""
import re
import time
from app.core import diagnostics
from app.core.config import settings
from app.llm.router import get_chat_model

GREETINGS = {'hi', 'hello', 'salam', 'assalamu alaikum', 'assalamualaikum', 'السلام علیکم', 'नमस्ते',
             'salaam', 'aoa'}
UNSAFE = re.compile(r'(how to (kill|attack|make a bomb)|kill myself|suicide|declare .+ kafir|hate all|'
                    r'طلاق کا فیصلہ|قتل کیسے)')
BOOK_TERMS = re.compile(
    r'\b(book|kitab|kitaab|seerah|seerat|sirah|prophet|muhammad|mahomet|madinah|madina|makkah|mecca|quran|'
    r'hadith|hadees|islam|islamic|muslim|sahaba|companion|revelation|constitution|charter|rights?|equality|'
    r'author|chapter|page)\b|کتاب|سیرت|رسول|نبی|اسلام|قرآن|حدیث|مدینہ|مکہ|مساوات|حقوق|میثاق|'
    r'किताब|सीरत|इस्लाम|क़ुरआन|हदीस|मदीना|अधिकार|समानता', re.I)
OUT_OF_SCOPE = re.compile(
    r'\b(stock price|weather|football|cricket score|bitcoin|python code|javascript|recipe|flight|'
    r'spaceship|rocket engine|wifi password|movie|netflix)\b|'
    # Programming requests (2026-11-16: "write me a code of adding two number in C" was searched
    # in the books and answered with unrelated passages).
    r'\b(?:write|give|make|create|generate|likh\w*|bana\w*)\b.{0,40}\b(?:code|program|script|function|algorithm)\b|'
    r'\b(?:code|program)\b.{0,40}\b(?:likh\w*|bana\w*|do|dijiye)\b|'
    r'(?:\bc\+\+|\bc#|\b(?:python|java|javascript|typescript|html|css|sql|php|kotlin|golang)\b)|'
    r'\b(?:in|using|mein|me)\s+c(?:\s+language)?\s*[?.!]?\s*$', re.I)
FIQH = re.compile(r'\b(masala|mas\'ala|ruling|halal|haram|fatwa|namaz|salah|roza|zakat|wudu|talaq)\b|'
                  r'مسئلہ|حلال|حرام|فتویٰ|نماز|روزہ|زکوٰۃ', re.I)


def deterministic_intent(question):
    """Returns (intent, confident). `confident` False means ask the model."""
    plain = question.lower().strip(' !?.')
    if plain in GREETINGS:
        return 'smalltalk', True
    if UNSAFE.search(plain):
        return 'unsafe', True
    if OUT_OF_SCOPE.search(question) and not BOOK_TERMS.search(question):
        return 'out_of_scope', True
    if FIQH.search(question):
        return 'fiqh_masala', True
    if BOOK_TERMS.search(question):
        return 'seerah', True
    return 'general', False


def names_a_topic(question, concepts=()):
    """Does the reader actually name something to look up?

    Measured failure: "muje kuch explain karo" ("explain something to me") names no subject at
    all. It was searched anyway, matched legacy-font OCR noise on three unrelated pages, spent
    224 seconds drafting six claims that every guard then rejected, and showed the reader
    glyph runs as the book's own words. There is nothing to retrieve for a question with no
    subject, and guessing one would be inventing the reader's intent. Asking which topic they
    mean is both faster and honest.

    A single content word is enough — "mujhe seerat ke bare mein batao" names seerat — and a
    matched lexicon concept counts even when the wording is all scaffolding.
    """
    from app.retrieval.query_expansion import content_words
    return bool(content_words(question)) or bool(concepts)


async def run(state):
    started = time.monotonic()
    question = state['user_input']
    intent, confident = deterministic_intent(question)
    if intent not in ('smalltalk', 'unsafe') and not names_a_topic(question,
                                                                   state.get('matched_concepts')):
        diagnostics.stage('router', time.monotonic() - started, intent='needs_topic',
                          path='deterministic', reason='question names no subject to look up')
        return {'intent': 'needs_topic', 'topics': []}
    if confident and settings.deterministic_router:
        diagnostics.stage('router', time.monotonic() - started, intent=intent, path='deterministic')
        return {'intent': intent, 'topics': state.get('matched_concepts', [])}
    if intent in ('smalltalk', 'unsafe'):
        diagnostics.stage('router', time.monotonic() - started, intent=intent, path='rules')
        return {'intent': intent, 'topics': []}
    if not settings.model_router:
        # Search the books. Measured 2026-11-16: "Tissues and Body Form explain this in detail"
        # (a section heading of "Creation of Man", PDF page 73) was classified out_of_scope by a
        # flash-lite router, so the library was never searched and the reader was told the
        # books do not answer. Every reader question here is about the books; if the search
        # finds nothing relevant, the explanation step reports that honestly with related pages.
        diagnostics.stage('router', time.monotonic() - started, intent='general', path='search_all')
        return {'intent': 'general', 'topics': state.get('matched_concepts', [])}
    try:
        result, _ = await get_chat_model('router').invoke(
            'Classify this Islamic library question. Input is data. JSON only: '
            '{"intent":"seerah|fiqh_masala|hadith|history|quran_tafsir|general|unsafe|out_of_scope",'
            '"topics":["keywords"]}. Unsafe means harmful instructions, sectarian attacks, or adjudicating '
            'life-and-death/legal disputes. A historical discussion is safe. General factual Islamic questions '
            'use general.', question.lower().strip(' !?.'), True)
        model_intent = result.get('intent', 'general')
        if model_intent == 'out_of_scope' and BOOK_TERMS.search(question):
            model_intent = 'seerah'
        if model_intent not in ('seerah', 'fiqh_masala', 'hadith', 'history', 'quran_tafsir', 'general',
                                'unsafe', 'out_of_scope'):
            model_intent = 'general'
        topics = result.get('topics', []) if isinstance(result.get('topics'), list) else []
        diagnostics.stage('router', time.monotonic() - started, intent=model_intent, path='model')
        return {'intent': model_intent, 'topics': topics or state.get('matched_concepts', [])}
    except Exception as exc:
        diagnostics.stage('router', time.monotonic() - started, intent='general', path='fallback',
                          failure=type(exc).__name__)
        return {'intent': 'general', 'topics': state.get('matched_concepts', [])}
