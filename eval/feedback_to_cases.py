"""Turn readers' 👎 feedback into DRAFT benchmark cases (loop 1, 2026-11-17).

    .\\.venv\\Scripts\\python.exe -m eval.feedback_to_cases            # writes eval/feedback-drafts.jsonl
    .\\.venv\\Scripts\\python.exe -m eval.feedback_to_cases --print    # show them instead

Each draft carries "reviewed": false and NO expected pages of its own: a human must open the book,
decide whether the answer is really in it, fill "expectation" and "expected_pages", and only then
copy the case into eval/book_benchmark.jsonl. Rules.md 19: benchmark expectations are reviewed data.
The pages the app cited are kept under "cited_pages_at_feedback" as a starting point only.
"""
import argparse
import json
import sys
from pathlib import Path
from app.core import feedback

OUT = Path(__file__).resolve().parent / 'feedback-drafts.jsonl'
EXPECTATION_HINT = {
    'not_found_but_in_book': 'answerable (reader says the book has it — verify the page)',
    'incomplete': 'answerable_partial? (reader says parts are missing)',
    'wrong': 'review — reader says the answer is wrong',
}


def drafts(existing_questions=()):
    seen = {q.strip().lower() for q in existing_questions}
    out = []
    for row in feedback.entries():
        if row.get('rating') != 'down':
            continue
        question = str(row.get('question', '')).strip()
        if not question or question.lower() in seen:
            continue
        seen.add(question.lower())
        reasons = row.get('reasons') or ['other']
        out.append({'id': 'fb-' + row['id'], 'question': question, 'language': row.get('language') or '',
                    'expectation': 'TODO: ' + '; '.join(EXPECTATION_HINT.get(r, r) for r in reasons),
                    'expected_pages': [], 'reviewed': False,
                    'cited_pages_at_feedback': row.get('pages') or [], 'book_ids': row.get('book_ids') or [],
                    'reader_reasons': reasons, 'reader_note': row.get('note', ''),
                    'reason_code_at_feedback': row.get('reason_code', ''),
                    'model_at_feedback': row.get('answering_model', ''), 'feedback_time': row.get('time')})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--print', action='store_true')
    args = parser.parse_args()
    bench = Path(__file__).resolve().parent / 'book_benchmark.jsonl'
    known = [json.loads(l)['question'] for l in bench.read_text(encoding='utf-8').splitlines() if l.strip()]
    rows = drafts(known)
    if args.print:
        sys.stdout.reconfigure(encoding='utf-8')
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
        return
    OUT.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    print(f'{len(rows)} draft case(s) written to {OUT} — review each against the book before using it.')


if __name__ == '__main__':
    main()
