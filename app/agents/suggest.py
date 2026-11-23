"""Follow-up questions and starter topics — "what can I ask next?" — at zero model cost.

Added 2026-11-17 (agent/GenAI upgrade). New readers do not know what the books contain, and
after an answer they do not know what to ask next. Two sources of suggestions, in order:

1. The answering model itself, in the SAME call as the answer: a hidden last-line marker
   `<<next: q1 | q2 | q3>>` (cloud models only — see explain_agent.user_message). It has just
   read the passages, so its questions are ones the sources can answer.
2. The book's own outline (app/ingestion/book_tree.py): the chapter/section that each cited
   page belongs to becomes "Explain «section» in detail". Used for local models, when the
   model gave no usable marker, and for "which topic?" (needs_topic) replies.

Suggestions are QUESTIONS, never statements, so they carry no grounding risk: clicking one
runs the normal retrieve → explain → audit pipeline.
"""
import re

NEXT = re.compile(r'<<\s*next\s*:(.*?)(?:>>|$)', re.I | re.S)
MAX_FOLLOWUPS = 3
MAX_LENGTH = 140

# Outline nodes that are not subjects a reader would want explained.
NOT_A_TOPIC = re.compile(r'^(?:فہرست|contents?|table of contents|index|indices|glossary|bibliography|'
                         r'references|preface|پیش لفظ|فہرست مضامین)\b', re.I)

EXPLAIN_TEMPLATE = {
    'English': 'Explain “{title}” in detail',
    'Hinglish': '“{title}” ko tafseel se samjhao',
    'Urdu': '«{title}» کو تفصیل سے سمجھائیے',
    'Hindi': '“{title}” को विस्तार से समझाइए',
}
SUMMARY_TEMPLATE = {
    'English': 'Give a summary of “{title}”',
    'Hinglish': '“{title}” ka khulasa batao',
    'Urdu': '«{title}» کا خلاصہ بیان کیجیے',
    'Hindi': '“{title}” का सारांश बताइए',
}


def split_followups(text):
    """(answer text without the marker, model-suggested questions)."""
    match = NEXT.search(text or '')
    if not match:
        return text, []
    body = (text[:match.start()] + text[match.end():]).rstrip()
    return body, clean(match.group(1).split('|'))


def clean(candidates, limit=MAX_FOLLOWUPS):
    out = []
    for raw in candidates:
        question = re.sub(r'\[\s*\d{1,2}\s*\]', '', str(raw))             # never a citation
        question = re.sub(r'\s+', ' ', question).strip(' -•*"“”\'')
        if not 6 <= len(question) <= MAX_LENGTH or '<<' in question or '>>' in question:
            continue
        if question.lower() not in {q.lower() for q in out}:
            out.append(question)
        if len(out) >= limit:
            break
    return out


def topic_title(title):
    """A clean, short section title ("باب 4: سیرت ..." -> "سیرت ...")."""
    title = re.sub(r'\s+', ' ', str(title or '')).strip()
    title = re.sub(r'^(?:باب|chapter)\s*[\w٠-٩]+\s*[:：-]\s*', '', title, flags=re.I)
    return title[:90].strip(' :-')


def from_outline(citations, language, exclude=(), limit=MAX_FOLLOWUPS):
    """'Explain «section»' for the sections the cited pages belong to, most-cited first."""
    from app.ingestion import book_tree
    template = EXPLAIN_TEMPLATE.get(language, EXPLAIN_TEMPLATE['English'])
    seen, out = {t.lower() for t in exclude}, []
    for citation in citations or []:
        place = book_tree.locate(citation.get('book_id', ''), int(citation.get('page') or 0))
        for title in (place.get('section'), place.get('chapter')):
            title = topic_title(title)
            if not title or NOT_A_TOPIC.match(title) or title.lower() in seen:
                continue
            seen.add(title.lower())
            out.append(template.format(title=title))
            break
        if len(out) >= limit:
            break
    return out


def starter_topics(language, limit=4):
    """Chapter-level starter questions across the library, for a reader who named no topic."""
    from app.ingestion import book_tree
    from app.ingestion.indexer import catalog
    template = EXPLAIN_TEMPLATE.get(language, EXPLAIN_TEMPLATE['English'])
    per_book = []
    for book in catalog():
        tree = book_tree.load(book['id']) or {}
        titles = [topic_title(c.get('title')) for c in tree.get('chapters', [])]
        per_book.append([t for t in titles if t and not NOT_A_TOPIC.match(t)])
    out = []
    # Round-robin across books so a two-book library shows both.
    while len(out) < limit and any(per_book):
        for titles in per_book:
            if titles and len(out) < limit:
                out.append(template.format(title=titles.pop(0)))
    return out


def followups_for(model_questions, citations, language):
    """Model suggestions first, then outline suggestions to fill up to three."""
    out = clean(model_questions)
    if len(out) < MAX_FOLLOWUPS:
        out += from_outline(citations, language, exclude=out, limit=MAX_FOLLOWUPS - len(out))
    return out[:MAX_FOLLOWUPS]


def outline(book_id):
    """Chapters and sections of one book for the chapter explorer (GET /books/{id}/outline)."""
    from app.ingestion import book_tree
    tree = book_tree.load(book_id)
    if not tree:
        return []
    chapters = []
    for chapter in tree.get('chapters', []):
        chapters.append({
            'id': chapter['id'], 'title': chapter['title'], 'topic': topic_title(chapter['title']),
            'page_start': chapter['page_start'], 'page_end': chapter['page_end'],
            'is_topic': not NOT_A_TOPIC.match(topic_title(chapter['title']) or ''),
            'sections': [{'id': s['id'], 'title': s['title'], 'topic': topic_title(s['title']),
                          'page_start': s['page_start'], 'page_end': s['page_end']}
                         for s in chapter.get('sections', [])],
        })
    return chapters


def topic_index():
    """Everything a reader can study, without a model call (loop 5, 2026-11-18).

    * concepts: the human-reviewed concepts of data/concept-lexicon.json with their surface forms in
      English / Urdu / Hindi / Hinglish (so a search for "equality" also finds the Urdu wording).
    * sections: every chapter and section of every book's outline, with its physical page range.
    No definitions are generated here: clicking a topic asks the book through the normal pipeline.
    """
    import json
    from app.core.config import ROOT
    from app.ingestion import book_tree
    from app.ingestion.indexer import catalog
    from app.agents.bibliography import display_title
    try:
        lexicon = json.loads((ROOT / 'data' / 'concept-lexicon.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        lexicon = []
    concepts = [{'id': c['id'], 'forms': {lang: list(forms)[:4] for lang, forms in (c.get('forms') or {}).items()}}
                for c in lexicon if isinstance(c, dict) and c.get('forms')]
    sections = []
    for book in catalog():
        tree = book_tree.load(book['id']) or {}
        title = display_title(book)
        for chapter in tree.get('chapters', []):
            chapter_topic = topic_title(chapter['title'])
            entries = [(chapter, '')] + [(s, chapter_topic) for s in chapter.get('sections', [])]
            for node, parent in entries:
                topic = topic_title(node['title'])
                if not topic or NOT_A_TOPIC.match(topic):
                    continue
                sections.append({'book_id': book['id'], 'book_title': title, 'title': node['title'], 'topic': topic,
                                 'kind': 'section' if parent else 'chapter', 'chapter': parent,
                                 'page_start': node['page_start'], 'page_end': node['page_end']})
    return {'concepts': concepts, 'sections': sections}
