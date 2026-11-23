"""Reader feedback on answers (👍 / 👎 + reason) — the quality loop. Added 2026-11-17 (loop 1).

Why: the benchmark (eval/book_benchmark.jsonl) is written by hand; the questions readers actually
ask, and the answers they find wrong or incomplete, are the most valuable new test cases. Each 👎
is stored locally and can be turned into a DRAFT benchmark case by
`eval/feedback_to_cases.py` — drafts are marked unreviewed and must be checked against the book
before they count (Rules.md 19: benchmark expectations are reviewed data, not targets).

Storage: data/feedback/feedback.jsonl, one JSON object per line, append-only, on this computer
only. It holds the question, the first part of the answer and the cited pages — the reader chose
to send them by pressing the button. Nothing is sent anywhere.
"""
import json
import threading
import time
import uuid
from app.core.config import ROOT

FEEDBACK_DIR = ROOT / 'data' / 'feedback'
FEEDBACK_FILE = FEEDBACK_DIR / 'feedback.jsonl'
REASONS = ('wrong', 'incomplete', 'not_found_but_in_book', 'wrong_language', 'too_long', 'too_short',
           'bad_reference', 'other')
_lock = threading.Lock()


def record(entry):
    """Append one validated feedback entry; returns it with id and timestamp."""
    row = {'id': uuid.uuid4().hex[:12], 'time': time.strftime('%Y-%m-%dT%H:%M:%S'), **entry}
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    with _lock, FEEDBACK_FILE.open('a', encoding='utf-8') as file:
        file.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def entries():
    if not FEEDBACK_FILE.exists():
        return []
    out = []
    for line in FEEDBACK_FILE.read_text(encoding='utf-8').splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue          # a torn last line after a crash must not break the summary
    return out


def summary(limit=20):
    rows = entries()
    down = [r for r in rows if r.get('rating') == 'down']
    by_reason = {}
    for row in down:
        for reason in row.get('reasons') or ['other']:
            by_reason[reason] = by_reason.get(reason, 0) + 1
    return {'total': len(rows), 'up': sum(1 for r in rows if r.get('rating') == 'up'), 'down': len(down),
            'down_by_reason': dict(sorted(by_reason.items(), key=lambda kv: -kv[1])),
            'recent_down': [{k: r.get(k) for k in ('id', 'time', 'question', 'reasons', 'note', 'pages',
                                                     'reason_code', 'answering_model')} for r in down[-limit:]][::-1]}
