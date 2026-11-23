"""Saved answers (bookmarks) — added 2026-11-17, improvement loop iteration 2.

The reader presses "☆ Save" on an answer to keep it with its citations, independent of the
conversation it came from (a conversation can be deleted; a saved answer stays until the reader
removes it). Stored on this computer only in data/saved/saved.json, written atomically
(temp file + replace) so a crash never leaves half a file. At most MAX_SAVED answers are kept.
"""
import json
import os
import threading
import time
import uuid
from app.core.config import ROOT

SAVED_DIR = ROOT / 'data' / 'saved'
SAVED_FILE = SAVED_DIR / 'saved.json'
MAX_SAVED = 500
_lock = threading.Lock()


def _read():
    try:
        data = json.loads(SAVED_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _write(items):
    SAVED_DIR.mkdir(parents=True, exist_ok=True)
    temp = SAVED_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(temp, SAVED_FILE)


def add(entry):
    with _lock:
        items = _read()
        # Saving the same answer twice returns the existing bookmark instead of a duplicate.
        same = next((i for i in items if i['question'] == entry['question'] and i['answer'] == entry['answer']), None)
        if same:
            return same, False
        item = {'id': uuid.uuid4().hex[:12], 'saved_at': time.strftime('%Y-%m-%dT%H:%M:%S'), **entry}
        items.append(item)
        _write(items[-MAX_SAVED:])
        return item, True


def listing():
    """Newest first, without the full answer and citations (the list stays small)."""
    out = []
    for item in reversed(_read()):
        preview = ' '.join(str(item.get('answer', '')).split())[:220]
        out.append({k: item.get(k) for k in ('id', 'saved_at', 'question', 'language', 'verification',
                                              'answering_model', 'session_id', 'answer_style')}
                   | {'preview': preview, 'pages': [c.get('page') for c in item.get('citations') or []][:12]})
    return out


def get(item_id):
    return next((i for i in _read() if i['id'] == item_id), None)


def remove(item_id):
    with _lock:
        items = _read()
        kept = [i for i in items if i['id'] != item_id]
        if len(kept) == len(items):
            return False
        _write(kept)
        return True
