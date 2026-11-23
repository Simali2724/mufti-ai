"""Paragraph/heading-aware child segments with parent paragraphs and page provenance.

Search runs over small child segments; answering fetches the parent paragraph block and
neighbouring context. Physical PDF page numbers and printed page labels are kept apart:
`page` is always the physical 1-based PDF page, `printed_label` is whatever the scan prints.
Raw OCR text is never rewritten here; corrections live in data/book-corrections and are
recorded with provenance so a reader can always see which text was changed and by whom.
"""
import json
import re
import unicodedata
from app.core.config import ROOT

CORRECTIONS_DIR = ROOT / 'data/book-corrections'
EASTERN_DIGITS = {ord(c): str(i) for i, c in enumerate('۰۱۲۳۴۵۶۷۸۹')}
EASTERN_DIGITS.update({ord(c): str(i) for i, c in enumerate('٠١٢٣٤٥٦٧٨٩')})
ENGLISH_MARKER = 'English text on this page:'
HEADING_RE = re.compile(r'^\s*[)(]?\s*[٠-٩۰-۹\d]{1,3}\s*[)(]?\s*[؀-ۿ]', re.M)
SECTION_RE = re.compile(r'^(?:باب|فصل|مبحث|حصہ|عنوان|chapter|section)\b', re.I)


def printed_label(text):
    """The page number printed on the scan, if a header/footer line clearly shows one."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in (lines[:1] + lines[-1:]):
        digits = re.findall(r'[٠-٩۰-۹]{1,4}|\b\d{1,4}\b', line)
        if not digits:
            continue
        value = digits[-1].translate(EASTERN_DIGITS)
        if value.isdigit() and 0 < int(value) < 2000:
            return int(value)
    return None


def heading_for(text):
    for line in text.splitlines()[:12]:
        line = line.strip()
        if SECTION_RE.match(line):
            return line[:150]
    for line in text.splitlines()[:12]:
        line = line.strip()
        if 6 <= len(line) <= 90 and HEADING_RE.match(line) and not line.endswith(('۔', '.')):
            return line[:150]
    return ''


def blocks(text):
    """Blank-line separated blocks, with the English layer kept as its own block."""
    body, english = text, ''
    if ENGLISH_MARKER in text:
        body, _, english = text.partition(ENGLISH_MARKER)
    out = [b.strip() for b in re.split(r'\n\s*\n', body) if b.strip()]
    english = english.strip()
    if english:
        # The embedded English layer is clean text: split it by sentence groups, not lines.
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', english) if s.strip()]
        buffer = ''
        for sentence in sentences:
            if len(buffer) + len(sentence) > 700 and buffer:
                out.append(buffer.strip())
                buffer = ''
            buffer += sentence + ' '
        if buffer.strip():
            out.append(buffer.strip())
    return out


def parents(text, target=900):
    """Group blocks into coherent parent paragraph units of roughly `target` characters."""
    groups, current = [], []
    for block in blocks(text):
        if current and sum(len(b) for b in current) + len(block) > target:
            groups.append('\n'.join(current))
            current = []
        current.append(block)
    if current:
        groups.append('\n'.join(current))
    return groups or ([text.strip()] if text.strip() else [])


def children(parent_text, size=440, overlap=110):
    """Overlapping child windows inside one parent, broken on sentence/line boundaries.

    Every child must stay a contiguous run of its parent (line breaks become spaces). The
    carried overlap is tracked explicitly: when the final remainder is too short to stand on
    its own it is folded into the previous child WITHOUT repeating that overlap, which used to
    duplicate a sentence inside the child and break the child-in-parent invariant.
    """
    if len(parent_text) <= size:
        return [parent_text]
    pieces = [p for p in re.split(r'(?<=[۔؟.!?])\s+|\n', parent_text) if p.strip()]
    out, current, carried = [], '', ''
    for piece in pieces:
        if len(current) + len(piece) + 1 > size and current:
            out.append(current.strip())
            tail = current[-overlap:]
            carried = tail[tail.find(' ') + 1:] if ' ' in tail else ''
            current = carried
        current += piece + ' '
    remainder = current.strip()
    if remainder:
        if out and len(remainder) < overlap:
            overlapping = carried.strip()
            fresh = remainder[len(overlapping):].strip() if overlapping and remainder.startswith(overlapping) \
                else remainder
            if fresh:
                out[-1] = (out[-1] + ' ' + fresh).strip()
        else:
            out.append(remainder)
    return out


def corrections_for(book_id):
    path = CORRECTIONS_DIR / f'{book_id}.json'
    if not path.exists():
        return {}
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except ValueError:
        return {}
    return {int(entry['page']): entry for entry in record.get('pages', []) if entry.get('corrected_text')}


def page_units(page, book, corrections=None):
    """Yield child segments for one page, each carrying its parent text and provenance."""
    correction = (corrections or {}).get(page['page'])
    raw_text = page['text']
    text = correction['corrected_text'] if correction else raw_text
    if not text.strip():
        return
    label = printed_label(text)
    heading = heading_for(text)
    for parent_index, parent_text in enumerate(parents(text)):
        parent_id = f"{book['id']}-p{page['page']}-{parent_index}"
        for child_index, child_text in enumerate(children(parent_text)):
            yield {
                'id': f'{parent_id}-{child_index}',
                'text': child_text,
                'parent_id': parent_id,
                'parent_text': parent_text,
                'parent_index': parent_index,
                'book_id': book['id'],
                'book_title': book['title'],
                'page_start': page['page'],
                'page_end': page['page'],
                'printed_label': label,
                'chapter': heading,
                'language': 'Urdu',
                'ocr': bool(page.get('ocr', False)),
                'corrected': bool(correction),
                'correction_source': correction.get('source', '') if correction else '',
                'correction_reviewer': correction.get('reviewer', '') if correction else '',
            }


def ascii_ratio(text):
    letters = [c for c in text if c.isalpha()]
    return sum(c.isascii() for c in letters) / max(1, len(letters))


def quality(text):
    """Heuristic extraction quality for one page; high is better. Never rewrites text."""
    if not text.strip():
        return {'score': 0.0, 'flags': ['empty']}
    flags = []
    letters = [c for c in text if c.isalpha()]
    arabic = sum('؀' <= c <= 'ۿ' for c in letters)
    words = [w for w in text.split() if w]
    arabic_ratio = arabic / max(1, len(letters))
    # Isolated one-character tokens are the usual signature of broken Nastaliq OCR.
    stray = sum(1 for w in words if len(w) == 1 and not w.isdigit()) / max(1, len(words))
    replacement = text.count('�')
    control = sum(1 for c in text if unicodedata.category(c) == 'Cc' and c not in '\n\r\t')
    score = 1.0
    if len(letters) < 120:
        score -= .35
        flags.append('very_short')
    if arabic_ratio < .3 and ascii_ratio(text) < .9:
        score -= .3
        flags.append('mixed_script_noise')
    if stray > .18:
        score -= .3
        flags.append('fragmented_tokens')
    if replacement:
        score -= min(.3, replacement * .05)
        flags.append('replacement_characters')
    if control:
        score -= .1
        flags.append('control_characters')
    if ENGLISH_MARKER not in text and arabic_ratio > .3 and len(letters) > 200:
        flags.append('no_english_layer')
    return {'score': round(max(0.0, score), 3), 'flags': flags, 'arabic_ratio': round(arabic_ratio, 3),
            'stray_token_ratio': round(stray, 3), 'letters': len(letters)}
