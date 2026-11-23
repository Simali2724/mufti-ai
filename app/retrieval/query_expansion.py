"""Controlled query variants: the original question plus auditable, provenance-tagged forms.

Every variant records where it came from, so a trace shows exactly which wording found a
passage. Variants only add search queries; they never merge distinct concepts. A lexicon
entry lists surface forms of ONE concept across scripts. Genuinely different but adjacent
concepts go under `related`, are searched separately, and their hits are marked as related
material rather than treated as the same idea.
"""
import json
import re
from app.core.config import ROOT
from app.ingestion.normalize import tokens

LEXICON_PATH = ROOT / 'data/concept-lexicon.json'

# A long natural question dilutes BM25: its few high-information words are outvoted by the
# many low-information ones. Measured on this book, "sanitation" alone ranks the right page
# first while the same word inside "What does the book say about sanitation and street
# lighting in Madinah?" does not place that page in the top 30 at all. So the question's own
# content words are searched as one ADDITIONAL auditable variant. Nothing is removed from the
# original query, no book-specific term is introduced, and the variant carries its own origin
# tag so a trace shows when it was the wording that found a passage.
QUESTION_WORDS = frozenset("""
a an the this that these those there here of in on at to for from by with about into over under
as is are was were be been being am do does did doing have has had having get gets
what which who whom whose when where why how whether
and or but not no nor so than then also such only just very more most some any all both each
i me my mine we us our ours you your yours he him his she her hers it its they them their theirs
say says said tell tells told explain explains explained describe describe describes described
give gives given mention mentions mentioned write writes written written state states stated
book books kitab kitaab according anything something
can could should would may might must shall will
detail details detailed please kindly something anything everything
""".split())
QUESTION_WORDS_URDU = frozenset("""
کیا کیوں کیسے کون کس کب کہاں ہے ہیں تھا تھے تھی ہوں ہوا ہوئی ہوتی ہوتا کا کی کے کو سے میں پر
اور یا نہ نہیں بارے متعلق بتائیں بتاؤ بیان گئی گیا کرتی کرتا کہتا کہتی کہا کتاب اس یہ وہ ان
کوئی بھی تک لیے لئے ساتھ والے والی ہی تو جو
""".split())
QUESTION_WORDS_HINDI = frozenset("""
क्या क्यों कैसे कौन किस कब कहाँ कहां है हैं था थे थी हूँ हुआ हुई होता होती का की के को से में
पर और या नहीं बारे बताइए बताएं बताओ कहा गया गई किताब इस यह वह उन कोई भी तक लिए साथ जो तो ही
""".split())
QUESTION_WORDS_HINGLISH = frozenset("""
kya kyun kyon kaise kaun kis kab kahan hai hain tha the thi hua hui hota hoti ka ki ke ko se
mein par aur ya nahi nahin baare bare mutalliq batao bataiye bataye likha likhi gaya gayi
kitab kitaab is yeh ye woh wo un koi bhi tak liye saath jo to hi mera apne
muje mujhe mujhko kuch kuchh karo karen kariye kijiye kijiye zara please thoda sab
samjhao samjhaiye samjha bata bataye sunao likho dikhao
""".split())
ALL_QUESTION_WORDS = (QUESTION_WORDS | QUESTION_WORDS_URDU | QUESTION_WORDS_HINDI
                      | QUESTION_WORDS_HINGLISH)
MIN_CONTENT_WORDS = 2

NAME_ALIASES = [
    (r'\b(?:mahomet|mohammed|mohammad|muhammed|muhammad)\b', 'Muhammad', ['حضرت محمد', 'رسول اللہ']),
    (r'\b(?:madina|madinah|medina)\b', 'Madinah', ['مدینہ']),
    (r'\b(?:mecca|makkah|makka)\b', 'Makkah', ['مکہ']),
    (r'\b(?:quran|qur\'an|koran)\b', 'Quran', ['قرآن']),
    (r'\b(?:seerah|seerat|sirah|sira)\b', 'Seerah', ['سیرت']),
    (r'\b(?:hadith|hadees)\b', 'Hadith', ['حدیث']),
]


def load_lexicon():
    if LEXICON_PATH.exists():
        try:
            return json.loads(LEXICON_PATH.read_text(encoding='utf-8'))
        except ValueError:
            return []
    return []


def canonical_names(query):
    """Normalise common spellings without discarding the user's wording."""
    out = query
    scripts = []
    for pattern, replacement, urdu in NAME_ALIASES:
        if re.search(pattern, out, re.I):
            out = re.sub(pattern, replacement, out, flags=re.I)
            scripts.extend(urdu)
    return out, scripts


def _matches(query_tokens, raw_query, forms):
    for form in forms:
        form_tokens = tokens(form)
        if not form_tokens:
            continue
        if all(t in query_tokens for t in form_tokens):
            return form
        if form in raw_query:
            return form
    return None


def concept_variants(query):
    """Lexicon-driven variants for concepts the question actually mentions."""
    query_tokens = set(tokens(query))
    variants, related, concepts = [], [], []
    for entry in load_lexicon():
        forms = [f for group in entry.get('forms', {}).values() for f in group]
        matched = _matches(query_tokens, query, forms)
        if not matched:
            continue
        concepts.append(entry['id'])
        for language, group in entry.get('forms', {}).items():
            for form in group:
                if form != matched:
                    variants.append({'text': form, 'origin': f"lexicon:{entry['id']}", 'language': language,
                                     'relation': 'same_concept'})
        for item in entry.get('related', []):
            related.append({'text': item['text'], 'origin': f"lexicon:{entry['id']}:related",
                            'language': item.get('language', ''), 'relation': 'related_concept',
                            'note': item.get('note', '')})
    return variants, related, concepts


def expand_query(query, translations=()):
    """Return (canonical query, variants, matched concept ids).

    `translations` are model-produced rewrites; they are kept but tagged, so a noisy
    machine translation can be told apart from the user's own words in any trace.
    """
    canonical, scripts = canonical_names(query)
    variants = [{'text': s, 'origin': 'name_alias', 'language': 'Urdu', 'relation': 'same_concept'} for s in scripts]
    concept, related, concepts = concept_variants(canonical)
    variants += concept
    for item in translations:
        text = str(item).strip()
        if text and text.lower() != canonical.lower():
            variants.append({'text': text, 'origin': 'llm_translation', 'language': '', 'relation': 'same_concept'})
    seen, unique = set(), []
    for item in variants + related:
        key = ' '.join(tokens(item['text'])) or item['text']
        if key in seen or not key:
            continue
        seen.add(key)
        unique.append(item)
    return canonical, unique, concepts


def content_words(query):
    """The question's own topic words, with interrogative scaffolding removed.

    Separate from `content_query` because the two answer different questions. This one asks
    "does the reader name a subject at all?", so a single word is a real answer: "mujhe seerat
    ke bare mein batao" names seerat. `content_query` asks "is there a useful extra lexical
    query here?", which needs at least two words to be worth running.
    """
    kept, seen = [], set()
    for token in tokens(query):
        if len(token) < 2 or token in ALL_QUESTION_WORDS or token in seen:
            continue
        seen.add(token)
        kept.append(token)
    return kept


def content_query(query):
    """The question's own content words, with interrogative scaffolding removed.

    Returns '' when it would not add anything: no word survives, too few words to be a useful
    lexical query, or it is just the original query again. Only the user's words are used.
    """
    kept = content_words(query)
    if len(kept) < MIN_CONTENT_WORDS:
        return ''
    reduced = ' '.join(kept)
    return '' if reduced == ' '.join(tokens(query)) else reduced


def search_queries(canonical, variants, limit=7):
    """The query strings actually sent to the retrievers, original first.

    Order matters: the original question, then its content words, then reviewed same-concept
    forms, then adjacent related concepts. `limit` bounds the embedding and BM25 work per
    request, so the most trustworthy wordings come first.
    """
    out = [{'text': canonical, 'origin': 'original', 'language': '', 'relation': 'same_concept'}]
    reduced = content_query(canonical)
    if reduced:
        out.append({'text': reduced, 'origin': 'content_words', 'language': '',
                    'relation': 'same_concept'})
    same = [v for v in variants if v['relation'] == 'same_concept']
    other = [v for v in variants if v['relation'] != 'same_concept']
    return (out + same + other)[:limit]
