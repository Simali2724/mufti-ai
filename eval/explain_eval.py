"""Answer-stage evaluation of the explanation path over the human-reviewed benchmark.

    .venv\\Scripts\\python.exe -u -m eval.explain_eval --mode gemini --out eval\\explain-eval-gemini.json
    .venv\\Scripts\\python.exe -u -m eval.explain_eval --mode gemini --ids ge-ur-1,piety-en-1 --resume

Measures, per case and in total:
  answered            the app gave a grounded, cited answer
  false_refusal       an answerable case that was not answered
  answered_absent     a case whose topic the book does not cover, answered anyway (bad)
  page_hit            at least one cited page is one of the reviewed expected pages
  latency, audit changes/removals, word count

Expected pages are human-reviewed data (eval/book_benchmark.jsonl), never fed to the app.
Run this with the server STOPPED on this machine: two processes driving Ollama on a 2 GB GPU
wedge it (see Memory.md). The saved model preference on disk is never changed by --mode.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

BENCHMARK = Path(__file__).with_name('book_benchmark.jsonl')


def load_cases(ids=None, holdout=True):
    rows = [json.loads(line) for line in BENCHMARK.read_text(encoding='utf-8').splitlines() if line.strip()]
    if ids:
        wanted = set(ids)
        rows = [r for r in rows if r['id'] in wanted]
    if not holdout:
        rows = [r for r in rows if not r.get('holdout')]
    return rows


def answerable(case):
    return not str(case.get('expectation', '')).startswith(('absent', 'not_', 'unanswerable', 'none'))


async def run_case(graph, case):
    from app.agents.graph import ask
    from app.core.schemas import ChatRequest
    started = time.monotonic()
    try:
        response = await ask(graph, ChatRequest(question=case['question'], session_id=f"eval-{time.time_ns()}"))
    except Exception as exc:
        return {'id': case['id'], 'error': type(exc).__name__, 'seconds': round(time.monotonic() - started, 1)}
    # Book-aware: page numbers repeat across books (page 33 exists in both).
    book = case.get('book')
    cited = [c.page for c in response.citations if not book or c.book_id == book]
    other_books = sorted({c.book_id for c in response.citations if book and c.book_id != book})
    expected = case.get('expected_pages') or []
    return {
        'id': case['id'], 'language': case.get('language'), 'expectation': case.get('expectation'),
        'question': case['question'], 'answered': response.grounded, 'reason_code': response.reason_code,
        'coverage': response.coverage, 'verification': response.verification,
        'cited_pages': cited, 'expected_pages': expected, 'other_books_cited': other_books,
        'page_hit': bool(set(cited) & set(expected)) if expected else None,
        'answering': f'{response.answering_provider}/{response.answering_model}',
        'fallback': response.fallback_reason, 'seconds': round(response.latency_ms / 1000, 1),
        'words': len(response.answer.split()), 'answer': response.answer,
    }


def summarise(results, cases):
    by_id = {c['id']: c for c in cases}
    done = [r for r in results if 'error' not in r]
    ans = [r for r in done if answerable(by_id[r['id']])]
    absent = [r for r in done if not answerable(by_id[r['id']])]
    hits = [r for r in ans if r['answered'] and r['page_hit'] is not None]
    service = [r for r in ans if r['reason_code'] in ('provider_unavailable', 'provider_quota_exhausted')]
    rate = lambda n, d: round(n / d, 3) if d else None
    return {
        'cases_run': len(done), 'errors': len(results) - len(done),
        'answerable': len(ans), 'answered': sum(r['answered'] for r in ans),
        'answered_rate': rate(sum(r['answered'] for r in ans), len(ans)),
        'false_refusals': [r['id'] for r in ans if not r['answered'] and r not in service],
        'service_failures': [r['id'] for r in service],
        'page_hit_rate_of_answered': rate(sum(r['page_hit'] for r in hits), len(hits)),
        'absent_cases': len(absent), 'answered_absent': [r['id'] for r in absent if r['answered']],
        'median_seconds': sorted(r['seconds'] for r in done)[len(done) // 2] if done else None,
        'audited': sum(r.get('verification') == 'audited' for r in done),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='', choices=['', 'auto', 'anthropic', 'openai', 'gemini', 'ollama'])
    parser.add_argument('--ids', default='')
    parser.add_argument('--out', default='')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--delay', type=float, default=6.0, help='seconds between cases (cloud rate limits)')
    parser.add_argument('--no-holdout', action='store_true')
    args = parser.parse_args()
    if args.mode:
        from app.llm import preferences
        saved = preferences.get_preferences()
        override = saved.model_copy(deep=True, update={'mode': args.mode})
        preferences.get_preferences = lambda: override.model_copy(deep=True)
        print('provider override for this run only:', args.mode, '| saved preference:', saved.mode)
    cases = load_cases([i for i in args.ids.split(',') if i] or None, holdout=not args.no_holdout)
    out = Path(args.out or Path(__file__).with_name(f"explain-eval-{args.mode or 'saved'}.json"))
    results = []
    if args.resume and out.exists():
        results = json.loads(out.read_text(encoding='utf-8')).get('results', [])
    finished = {r['id'] for r in results if 'error' not in r}
    results = [r for r in results if r['id'] in finished]
    from app.agents.graph import graph_context
    async with graph_context() as graph:
        for number, case in enumerate(cases, start=1):
            if case['id'] in finished:
                continue
            result = await run_case(graph, case)
            results.append(result)
            print(f"[{number}/{len(cases)}] {case['id']:<12} answered={result.get('answered')} "
                  f"reason={result.get('reason_code') or '-'} pages={result.get('cited_pages')} "
                  f"expected={case.get('expected_pages')} {result.get('seconds')}s", flush=True)
            out.write_text(json.dumps({'summary': summarise(results, cases), 'results': results},
                                      ensure_ascii=False, indent=1), encoding='utf-8')
            await asyncio.sleep(args.delay)
    summary = summarise(results, cases)
    out.write_text(json.dumps({'summary': summary, 'results': results}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print('saved', out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
