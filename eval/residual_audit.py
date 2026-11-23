"""Residual-error check: how many problems are LEFT in final answers after the app's own audit?
(Accuracy loop, 2026-11-18.)

The app's audit runs on a lite model under a 25 s budget. This script re-checks FINAL answers
(as the reader saw them) with a stronger model and the same AUDIT_RULES, against the text of the
pages each answer cites (`citations[].full_support`). It reports the share of sentences the
stronger judge still flags. Read-only: it never changes an answer or the history.

    # needs the server running (reads conversations over HTTP); costs one cloud call per answer
    .\\.venv\\Scripts\\python.exe -m eval.residual_audit --limit 6 --model gemini-2.5-flash
    .\\.venv\\Scripts\\python.exe -m eval.residual_audit --limit 6 --out eval\\residual-audit.json

Caveat recorded with every run: the original audit saw all evidence windows; this judge sees only
the cited pages, so a sentence supported only by an uncited window can be flagged here. Treat a
flag as "needs a human look", not as a proven error.
"""
import argparse
import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:786'


def candidate_turns(limit, skip=0):
    con = sqlite3.connect(f"file:{ROOT / 'data/index/sessions.sqlite'}?mode=ro", uri=True)
    threads = [r[0] for r in con.execute(
        'select thread_id, max(rowid) from checkpoints group by thread_id order by max(rowid) desc')]
    turns = []
    for thread in threads:
        try:
            history = httpx.get(f'{BASE}/sessions/{thread}', timeout=30).json().get('history', [])
        except Exception:
            continue
        for turn in reversed(history):
            if (turn.get('grounded') and turn.get('answer_format') == 'markdown' and turn.get('citations')
                    and all(c.get('full_support') for c in turn['citations'])):
                turns.append({'session': thread, **turn})
                break                       # one answer per conversation keeps the sample varied
        if len(turns) >= limit + skip:
            break
    return turns[skip:]


async def judge_call(model, system, user, schema, attempts=2):
    """Direct Gemini call for the judge. Measured 2026-11-18: gemini-3-flash-preview timed out through
    the app's 180 s client under high demand, then answered in 2.3 s with thinkingLevel=low and 7.4 s
    without. The judge uses low thinking on Gemini 3 models, a 240 s budget and one retry."""
    from app.core.config import settings
    generation = {'temperature': 0, 'responseMimeType': 'application/json', 'responseJsonSchema': schema}
    if model.startswith('gemini-3'):
        generation['thinkingConfig'] = {'thinkingLevel': 'low'}
    body = {'systemInstruction': {'parts': [{'text': system}]},
            'contents': [{'role': 'user', 'parts': [{'text': user}]}], 'generationConfig': generation}
    last = None
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=240, trust_env=False) as client:
                r = await client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                                      headers={'x-goog-api-key': settings.google_api_key}, json=body)
                r.raise_for_status()
                parts = r.json()['candidates'][0]['content']['parts']
                return ''.join(p.get('text', '') for p in parts if not p.get('thought'))
        except Exception as exc:
            last = exc
            await asyncio.sleep(5 * (attempt + 1))
    raise last


async def recheck(turn, model):
    from app.agents.explain_agent import sentence_units, cited_ids, CITE
    from app.llm.prompts import AUDIT_RULES
    from app.llm.providers import complete
    from app.llm.structured import SCHEMAS
    from json_repair import repair_json
    limit = max(c['id'] for c in turn['citations'])
    units = sentence_units(turn['answer'])
    payload = {'sources': [{'n': c['id'], 'pdf_page': c['page'], 'text': c['full_support'][:6000]}
                           for c in turn['citations']],
               'question': turn['question'],
               'sentences': [{'id': u['id'], 'text': CITE.sub('', u['text']).strip(),
                              'cites': cited_ids(u['text'], limit) or 'none'} for u in units]}
    started = time.monotonic()
    raw = await judge_call(model, AUDIT_RULES, json.dumps(payload, ensure_ascii=False), SCHEMAS['audit'])
    result = repair_json(raw, return_objects=True)
    problems = [p for p in (result.get('problems') or []) if isinstance(p, dict)] if isinstance(result, dict) else []
    by_id = {u['id']: u['text'] for u in units}
    return {'session': turn['session'], 'question': turn['question'], 'language': turn.get('language'),
            'verification_at_answer': turn.get('verification'), 'sentences': len(units),
            'uncited': sum(1 for u in units if not cited_ids(u['text'], limit)),
            'flagged': [{'id': p.get('id'), 'issue': p.get('issue'), 'sentence': by_id.get(p.get('id'), '')[:300],
                         'suggested_fix': str(p.get('fix', ''))[:300]} for p in problems],
            'seconds': round(time.monotonic() - started, 1)}


async def main_async(args):
    turns = candidate_turns(args.limit, args.skip)
    results = []
    for turn in turns:
        try:
            results.append(await recheck(turn, args.model))
        except Exception as exc:
            results.append({'session': turn['session'], 'question': turn['question'], 'error': type(exc).__name__})
        await asyncio.sleep(args.delay)
    ok = [r for r in results if 'error' not in r]
    sentences = sum(r['sentences'] for r in ok)
    flagged = sum(len(r['flagged']) for r in ok)
    summary = {'model': args.model, 'answers': len(ok), 'errors': len(results) - len(ok), 'sentences': sentences,
               'flagged': flagged, 'flag_rate': round(flagged / sentences, 3) if sentences else None,
               'uncited_sentences': sum(r['uncited'] for r in ok),
               'by_issue': {i: sum(1 for r in ok for f in r['flagged'] if f['issue'] == i)
                            for i in ('unsupported', 'misattributed', 'overstated', 'contradicted')},
               'caveat': 'judge sees only cited pages; a flag means "needs human review", not a proven error'}
    return {'summary': summary, 'results': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=6)
    parser.add_argument('--model', default='gemini-2.5-flash')
    parser.add_argument('--skip', type=int, default=0, help='skip the N newest answers (compare older vs newer)')
    parser.add_argument('--delay', type=float, default=4)
    parser.add_argument('--out', default='')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    report = asyncio.run(main_async(args))
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False, indent=1))
    for r in report['results']:
        for f in r.get('flagged', []):
            print(f"- [{f['issue']}] {r['question'][:50]} :: {f['sentence'][:160]}")


if __name__ == '__main__':
    main()
