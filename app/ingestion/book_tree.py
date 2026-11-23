"""Persistent Book -> Chapter -> Section -> physical page-range tree for each book.

Built from the PDF's own outline, which this book has and which nothing in the application
was using. That matters for two separate reasons.

**It is a real structure.** 310 outline entries, monotonically ordered, physical page targets
inside the document's 689 pages. The flat level-1 list encodes two tiers by marker: entries
carrying the chapter marker are chapters ("باب 1", "اِبتدائیہ"), and the entries between two
chapters are that chapter's sections. A section owns the page range from its own page up to
the next entry's page, bounded by its chapter's end, which is how a page is resolved back to
a section.

**Its titles are CLEAN.** The page text in this book comes from OCR over legacy InPage fonts
and is badly degraded: PDF page 50's body reads "اسلام اور مضرب کی معاشری اقدار کا فرق",
while the outline entry for the same page reads "اِسلام اور مغرب کی معاشرتی اَقدار کا فرق".
The outline is embedded text, not OCR, so it is the only correctly spelled Urdu in the
corpus. A reader who types correct Urdu cannot match the garbled body text but can match
these titles, which is why the tree is also a retrieval route and not only navigation.

No model is called anywhere in this file. The brief's warning applies in full: a heading
locates a section, it is never evidence for that section's substantive claims, so a tree hit
only ever contributes candidate pages and the answer is still drafted from the real
paragraphs on them. This is a PageIndex-INSPIRED chapter tree, not the official PageIndex
integration: see Architecture.md for the measured reasons that package was not adopted.
"""
import hashlib
import json
import re
from app.core.config import INDEX
from app.ingestion.indexer import catalog

TREES_DIR = INDEX / 'trees'
# The outline marks a chapter with this emoji, then "باب N:" or "اِبتدائیہ:".
CHAPTER_MARKER = '🔰'
CHAPTER_WORDS = ('باب', 'اِبتدائیہ', 'ابتدائیہ')
_cache = {}


def clean_title(title):
    return re.sub(r'\s+', ' ', str(title).replace(CHAPTER_MARKER, ' ')).strip()


def is_chapter(title):
    stripped = str(title)
    return CHAPTER_MARKER in stripped or any(stripped.lstrip().startswith(word)
                                             for word in CHAPTER_WORDS)


def node_id(book_id, kind, index):
    return f'{book_id}-{kind}{index}'


def build(book_id, pdf_path, page_count):
    """Read the PDF outline and return the persisted tree, or None when there is no outline."""
    import pymupdf
    with pymupdf.open(pdf_path) as doc:
        outline = doc.get_toc() or []
        page_count = page_count or doc.page_count
    entries = [{'level': level, 'title': clean_title(title), 'page': int(page)}
               for level, title, page in outline
               if clean_title(title) and 1 <= int(page) <= page_count]
    source = 'pdf_outline'
    reviewed = reviewed_outline(book_id, page_count)
    if reviewed:
        # A visually reviewed outline in data/book-metadata/<id>.json wins over the PDF's own.
        # "Creation of Man" ships an outline of file names ("1.pdf", "2.pdf", ...), which would
        # have become its chapter titles (2026-11-16).
        entries, source = reviewed, 'reviewed_outline'
    if not entries:
        return None
    entries.sort(key=lambda e: e['page'])

    # Chapters first, so a section's range can be clipped to its own chapter.
    chapters, current = [], None
    for entry in entries:
        if entry.get('chapter', is_chapter(entry['title'])) or current is None:
            current = {'id': node_id(book_id, 'c', len(chapters) + 1), 'kind': 'chapter',
                       'title': entry['title'], 'page_start': entry['page'], 'sections': [],
                       'parent_id': book_id}
            chapters.append(current)
            continue
        current['sections'].append({'id': node_id(book_id, 's', sum(len(c['sections'])
                                                                    for c in chapters) + 1),
                                    'kind': 'section', 'title': entry['title'],
                                    'page_start': entry['page'], 'parent_id': current['id']})
    for index, chapter in enumerate(chapters):
        chapter['page_end'] = (chapters[index + 1]['page_start'] - 1
                               if index + 1 < len(chapters) else page_count)
        sections = chapter['sections']
        for position, section in enumerate(sections):
            section['page_end'] = (sections[position + 1]['page_start'] - 1
                                   if position + 1 < len(sections) else chapter['page_end'])
            # A heading can share a page with the next one; never invert the range.
            section['page_end'] = max(section['page_end'], section['page_start'])
    tree = {'book_id': book_id, 'page_count': page_count,
            'source': source, 'outline_entries': len(entries),
            'source_hash': source_hash(pdf_path), 'chapters': chapters,
            'problems': validate(chapters, page_count)}
    TREES_DIR.mkdir(parents=True, exist_ok=True)
    path(book_id).write_text(json.dumps(tree, ensure_ascii=False, indent=1), encoding='utf-8')
    _cache.pop(book_id, None)
    return tree


def reviewed_outline(book_id, page_count):
    """Outline entries from the reviewed book metadata, or [] when there are none."""
    try:
        record = json.loads((INDEX.parent / 'book-metadata' / f'{book_id}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    return [{'level': 1, 'title': clean_title(e['title']), 'page': int(e['page']), 'chapter': bool(e.get('chapter'))}
            for e in record.get('outline') or []
            if e.get('title') and 1 <= int(e.get('page', 0)) <= page_count]


def source_hash(pdf_path):
    """Hash of the PDF the tree was built from, so a replaced book invalidates its tree."""
    digest = hashlib.sha256()
    with open(pdf_path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def validate(chapters, page_count):
    """Every problem found, not the first: a half-checked tree is worse than none."""
    problems = []
    for chapter in chapters:
        if not 1 <= chapter['page_start'] <= chapter['page_end'] <= page_count:
            problems.append(f"chapter {chapter['id']} range "
                            f"{chapter['page_start']}-{chapter['page_end']} outside 1-{page_count}")
        for section in chapter['sections']:
            if not chapter['page_start'] <= section['page_start'] <= section['page_end'] <= chapter['page_end']:
                problems.append(f"section {section['id']} range "
                                f"{section['page_start']}-{section['page_end']} outside its chapter")
            if section['parent_id'] != chapter['id']:
                problems.append(f"section {section['id']} has a broken parent link")
    return problems


def path(book_id):
    return TREES_DIR / f'{book_id}.json'


def is_stale(tree):
    """True when the book this tree was built from is not the book now catalogued.

    The tree records the SHA-256 of the PDF it read, and the catalogue records the SHA-256 of
    the PDF it indexed, both over the same bytes — so a replaced book is detectable by
    comparing two strings, with no need to re-hash 16 MB on every load. A stale tree is worse
    than none: it would caption a citation with a heading from a different edition.
    """
    if not tree:
        return False
    entry = next((b for b in catalog() if b['id'] == tree.get('book_id')), None)
    recorded = (entry or {}).get('hash', '')
    return bool(recorded) and bool(tree.get('source_hash')) and recorded != tree['source_hash']


def load(book_id):
    if book_id in _cache:
        return _cache[book_id]
    file = path(book_id)
    tree = None
    if file.exists():
        try:
            tree = json.loads(file.read_text(encoding='utf-8'))
        except ValueError:
            tree = None
    if is_stale(tree):
        tree = None
    _cache[book_id] = tree
    return tree


def nodes(book_id):
    """Flat list of every chapter and section, each with its validated page range."""
    tree = load(book_id)
    if not tree:
        return []
    out = []
    for chapter in tree['chapters']:
        out.append({k: v for k, v in chapter.items() if k != 'sections'})
        out.extend(chapter['sections'])
    return out


def locate(book_id, page):
    """The chapter and section a physical page belongs to, for display and navigation."""
    tree = load(book_id)
    if not tree:
        return {}
    for chapter in tree['chapters']:
        if not chapter['page_start'] <= page <= chapter['page_end']:
            continue
        section = next((s for s in chapter['sections']
                        if s['page_start'] <= page <= s['page_end']), None)
        return {'chapter_id': chapter['id'], 'chapter': chapter['title'],
                'section_id': section['id'] if section else '',
                'section': section['title'] if section else '',
                'page_start': (section or chapter)['page_start'],
                'page_end': (section or chapter)['page_end']}
    return {}


def build_all():
    """(Re)build the tree for every catalogued book. Returns one report per book."""
    report = []
    for book in catalog():
        pdf = book.get('path') or str(INDEX.parent / 'books' / book['filename'])
        try:
            tree = build(book['id'], pdf, book.get('pages'))
        except Exception as exc:
            report.append({'book_id': book['id'], 'error': f'{type(exc).__name__}: {exc}'})
            continue
        if tree is None:
            report.append({'book_id': book['id'], 'outline_entries': 0,
                           'note': 'no PDF outline; tree route unavailable for this book'})
            continue
        report.append({'book_id': book['id'], 'outline_entries': tree['outline_entries'],
                       'chapters': len(tree['chapters']),
                       'sections': sum(len(c['sections']) for c in tree['chapters']),
                       'problems': tree['problems']})
    return report


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(build_all(), ensure_ascii=False, indent=1))
