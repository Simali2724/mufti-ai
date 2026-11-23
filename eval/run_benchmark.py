"""Measure book-answer coverage against the human-reviewed benchmark.

Three modes, because they cost very different amounts of time on this machine:

  --retrieval  embeddings only, no answering model. Measures whether the reviewed pages
               reach the candidate pool and the evidence windows. Minutes.
  --answers    the whole pipeline. Measures false refusals, citation correctness,
               unsupported claims, coverage agreement and latency. Hours on a local model.
  --router     deterministic intent classifier against the model router, before trusting it.

Expected pages come from eval/book_benchmark.jsonl, which was written by reading the source
pages. Nothing here feeds an expected answer to the application; only the retrieved and
generated results are compared against the reviewed page list.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BENCHMARK = Path(__file__).with_name('book_benchmark.jsonl')


def load_cases(include_holdout=False, only=None):
    rows = [json.loads(line) for line in BENCHMARK.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not include_holdout:
        rows = [r for r in rows if not r.get('holdout')]
    if only:
        rows = [r for r in rows if r['id'] in set(only)]
    return rows


async def retrieval_pass(cases, top_k=None, max_windows=None):
    from app.agents import language_agent
    from app.retrieval.hybrid import search
    from app.retrieval.evidence import select
    from app.core.config import settings
    rows = []
    for case in cases:
        started = time.monotonic()
        state = {'user_input': case['question'], 'language_hint': 'auto', 'history': []}
        language = await language_agent.run(state)
        candidates, report = await search(language['search_queries'])
        windows, selection = select(candidates, token_budget=top_k or settings.evidence_token_budget,
                                    max_windows=max_windows,
                                    concepts=language['matched_concepts'])
        expected = set(case['expected_pages'])
        candidate_pages = [c['page_start'] for c in candidates]
        window_pages = selection['selected_pages']
        rows.append({
            'id': case['id'], 'question': case['question'], 'language': case['language'],
            'expectation': case['expectation'], 'expected_pages': sorted(expected),
            'candidate_pages': candidate_pages[:30], 'window_pages': window_pages,
            'candidate_hit': bool(expected & set(candidate_pages)),
            'window_hit': bool(expected & set(window_pages)),
            'top3_hit': bool(expected & set(window_pages[:3])),
            'variants': [v['text'] for v in language['search_queries']],
            'concepts': language['matched_concepts'],
            'seconds': round(time.monotonic() - started, 2),
        })
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    answerable = [r for r in rows if r['expectation'] != 'absent']
    summary = {
        'mode': 'retrieval', 'cases': len(rows), 'answerable': len(answerable),
        'candidate_recall': _rate(r['candidate_hit'] for r in answerable),
        'window_recall': _rate(r['window_hit'] for r in answerable),
        'top3_recall': _rate(r['top3_hit'] for r in answerable),
        'median_seconds': _median([r['seconds'] for r in rows]),
        'misses': [r['id'] for r in answerable if not r['window_hit']],
    }
    return rows, summary


def load_done(path):
    """Per-case results already on disk, so a long run resumes instead of starting over.

    On this machine a full --answers pass is hours and two earlier runs were lost outright at
    29/48 and 6/48 cases. Completed cases are now reread and skipped, and the file is rewritten
    after every case, so a shutdown costs one case rather than the whole evaluation.
    """
    if not path or not Path(path).exists():
        return []
    try:
        saved = json.loads(Path(path).read_text(encoding='utf-8'))
    except ValueError:
        return []
    return [r for r in saved.get('rows', []) if r.get('id')]


def save_progress(path, rows, summary):
    if path:
        Path(path).write_text(json.dumps({'summary': summary, 'rows': rows},
                                         ensure_ascii=False, indent=1), encoding='utf-8')


async def answer_pass(cases, done=(), out='', delay=0):
    from app.agents.graph import graph_context, ask
    from app.core.schemas import ChatRequest
    from app.ingestion.indexer import get_page
    rows = list(done)
    finished = {r['id'] for r in rows}
    pending = [c for c in cases if c['id'] not in finished]
    if finished:
        print(f'resuming: {len(finished)} cases already done, {len(pending)} to go', flush=True)
    async with graph_context() as graph:
        for position, case in enumerate(pending):
            # Pace the run. A free-tier cloud key rate-limits well below the speed this loop
            # can ask questions, and a 429 trips the circuit breaker, which silently falls the
            # request through to the local model. The run then measures two providers at once
            # and the summary means nothing. Waiting is cheaper than an unusable benchmark.
            if delay and position:
                await asyncio.sleep(delay)
            response = await ask(graph, ChatRequest(question=case['question'],
                                                   session_id=f'bench-{time.time_ns()}'))
            expected = set(case['expected_pages'])
            cited = [c.page for c in response.citations]
            quotes_real = all((c.full_support or c.excerpt).replace(' …', '') and
                              _quote_present(c, get_page) for c in response.citations)
            answerable = case['expectation'] != 'absent'
            row = {
                'id': case['id'], 'question': case['question'], 'language': case['language'],
                'expectation': case['expectation'], 'expected_pages': sorted(expected),
                'grounded': response.grounded, 'coverage': response.coverage,
                'reason_code': response.reason_code, 'cited_pages': cited,
                'evidence_pages': response.evidence_pages,
                'citation_pages_expected': bool(expected & set(cited)) if cited else False,
                'citations_verbatim': quotes_real,
                'false_refusal': answerable and not response.grounded,
                'answered_absent_topic': (not answerable) and response.grounded,
                'answering_model': response.answering_model, 'selected_model': response.selected_model,
                'fallback_reason': response.fallback_reason,
                'missing_aspects': response.missing_aspects,
                'latency_ms': response.latency_ms, 'answer': response.answer,
            }
            rows.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != 'answer'}, ensure_ascii=False), flush=True)
            save_progress(out, rows, {'mode': 'answers', 'cases': len(rows), 'in_progress': True})
    answerable_rows = [r for r in rows if r['expectation'] != 'absent']
    absent_rows = [r for r in rows if r['expectation'] == 'absent']
    cited_rows = [r for r in answerable_rows if r['cited_pages']]
    summary = {
        'mode': 'answers', 'cases': len(rows),
        'answered_rate': _rate(r['grounded'] for r in answerable_rows),
        'false_refusal_rate': _rate(r['false_refusal'] for r in answerable_rows),
        'answered_absent_topic_rate': _rate(r['answered_absent_topic'] for r in absent_rows),
        'citation_page_accuracy': _rate(r['citation_pages_expected'] for r in cited_rows),
        'citations_verbatim_rate': _rate(r['citations_verbatim'] for r in cited_rows),
        'coverage_counts': {c: sum(1 for r in rows if r['coverage'] == c) for c in ('full', 'partial', 'none')},
        'median_latency_ms': _median([r['latency_ms'] for r in rows]),
        'max_latency_ms': max([r['latency_ms'] for r in rows], default=0),
        'false_refusals': [r['id'] for r in answerable_rows if r['false_refusal']],
        'wrong_page_citations': [r['id'] for r in cited_rows if not r['citation_pages_expected']],
    }
    return rows, summary


def _quote_present(citation, get_page):
    page = get_page(citation.book_id, citation.page) or {}
    text = ' '.join(page.get('text', '').split())
    needle = ' '.join((citation.full_support or citation.excerpt).replace(' …', '').split())
    return bool(needle) and needle in text


async def router_pass(cases):
    from app.agents.router_agent import deterministic_intent, run as router_run
    from app.core.config import settings
    rows = []
    for case in cases:
        fast, confident = deterministic_intent(case['question'])
        settings.deterministic_router = False
        try:
            model = (await router_run({'user_input': case['question'], 'matched_concepts': []}))['intent']
        finally:
            settings.deterministic_router = True
        searches_book = fast not in ('smalltalk', 'unsafe', 'out_of_scope')
        model_searches_book = model not in ('smalltalk', 'unsafe', 'out_of_scope')
        rows.append({'id': case['id'], 'deterministic': fast, 'confident': confident, 'model': model,
                     'same_routing_decision': searches_book == model_searches_book,
                     'expectation': case['expectation']})
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    confident_rows = [r for r in rows if r['confident']]
    summary = {'mode': 'router', 'cases': len(rows), 'confident_cases': len(confident_rows),
               'routing_agreement_on_confident': _rate(r['same_routing_decision'] for r in confident_rows),
               'disagreements': [r['id'] for r in confident_rows if not r['same_routing_decision']]}
    return rows, summary


def _rate(values):
    values = list(values)
    return round(sum(bool(v) for v in values) / len(values), 3) if values else None


def _median(values):
    values = sorted(values)
    return values[len(values) // 2] if values else 0


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--retrieval', action='store_true')
    parser.add_argument('--answers', action='store_true')
    parser.add_argument('--router', action='store_true')
    parser.add_argument('--holdout', action='store_true', help='include the held-out questions')
    parser.add_argument('--no-model-rewrite', action='store_true',
                        help='skip the language-agent rewrite when there is no conversation history, '
                             'to measure what its machine translations are actually worth')
    parser.add_argument('--only', nargs='*', default=None)
    parser.add_argument('--out', default='')
    parser.add_argument('--windows', type=int, default=None,
                        help='evidence windows per case; the shipping default is '
                             'config evidence_windows. Earlier measurements in this repo used 8, '
                             'so pass 8 to compare against them like for like.')
    parser.add_argument('--delay', type=float, default=0,
                        help='seconds to wait between cases; use with a rate-limited cloud key '
                             'so a 429 does not silently fall the run through to the local model')
    parser.add_argument('--resume', action='store_true',
                        help='reuse per-case results already in --out and only run what is missing')
    # Measure a different provider WITHOUT editing the user's saved model-settings.json.
    parser.add_argument('--mode', default='', choices=['', 'auto', 'anthropic', 'openai',
                                                       'gemini', 'ollama'])
    args = parser.parse_args()
    if args.mode:
        from app.llm import preferences
        saved = preferences.get_preferences()
        override = saved.model_copy(deep=True, update={'mode': args.mode})
        preferences.get_preferences = lambda: override.model_copy(deep=True)
        print(f'provider override for this run only: {args.mode} '
              f'| saved preference on disk is still: {saved.mode}', flush=True)
    if args.no_model_rewrite:
        from app.core.config import settings
        settings.model_rewrite_without_history = False
    cases = load_cases(args.holdout, args.only)
    out_path = args.out or str(Path(__file__).with_name('benchmark-answers.json'))
    if args.answers:
        rows, summary = await answer_pass(cases, load_done(out_path) if args.resume else (),
                                          out_path, args.delay)
    elif args.router:
        rows, summary = await router_pass(cases)
    else:
        rows, summary = await retrieval_pass(cases, max_windows=args.windows)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    out = Path(args.out) if args.out else Path(__file__).with_name(f"benchmark-{summary['mode']}.json")
    out.write_text(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1), encoding='utf-8')
    print('saved', out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
