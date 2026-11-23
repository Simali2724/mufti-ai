"""Run the same questions end-to-end on each installed local answer model and compare.

Latency and answer quality on this machine depend heavily on which local model answers, and
the brief requires fitting context and output to the selected model and hardware rather than
assuming. This changes only the in-process preference for the duration of the run; the saved
model-settings.json is not touched.

Usage:
    .\.venv\Scripts\python.exe -m eval.compare_local_models qwen3:1.7b llama3.2:3b -- ge-en-1 piety-en-1
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def run_case(graph, case, model):
    from app.agents.graph import ask
    from app.core.schemas import ChatRequest
    from app.llm import preferences as prefs

    # graph.ask() opens model_request(), which re-reads get_preferences() and overwrites any
    # request_preferences already set. So the override has to replace get_preferences itself,
    # for this process only. The saved model-settings.json on disk is never written.
    saved = prefs.get_preferences()
    forced = saved.model_copy(deep=True)
    forced.mode = 'ollama'
    forced.models = {**forced.models, 'ollama': model}
    from app.llm import router as llm_router
    from app.agents import retriever_agent
    fake = lambda: forced.model_copy(deep=True)
    patched = [(prefs, 'get_preferences'), (llm_router, 'get_preferences'),
               (retriever_agent, 'get_preferences')]
    originals = [(module, name, getattr(module, name)) for module, name in patched]
    for module, name in patched:
        setattr(module, name, fake)
    try:
        started = time.monotonic()
        response = await ask(graph, ChatRequest(question=case['question'],
                                               session_id=f'cmp-{time.time_ns()}'))
    finally:
        for module, name, value in originals:
            setattr(module, name, value)
    expected = set(case['expected_pages'])
    cited = [c.page for c in response.citations]
    return {
        'model': model, 'id': case['id'], 'question': case['question'],
        'expectation': case['expectation'], 'expected_pages': sorted(expected),
        'grounded': response.grounded, 'coverage': response.coverage,
        'reason_code': response.reason_code, 'cited_pages': cited,
        'evidence_pages': response.evidence_pages,
        'cited_expected_page': bool(expected & set(cited)),
        'claims': len(response.citations),
        'missing_aspects': response.missing_aspects,
        'seconds': round(time.monotonic() - started, 1),
        'answer': response.answer,
    }


async def main():
    argv = sys.argv[1:]
    split = argv.index('--') if '--' in argv else len(argv)
    models = argv[:split] or ['qwen3:1.7b']
    only = argv[split + 1:] or None

    from eval.run_benchmark import load_cases
    from app.agents.graph import graph_context

    cases = load_cases(include_holdout=True, only=only)
    print(f'{len(cases)} case(s) x {len(models)} model(s)', flush=True)
    rows = []
    async with graph_context() as graph:
        for model in models:
            for case in cases:
                row = await run_case(graph, case, model)
                rows.append(row)
                print(json.dumps({k: v for k, v in row.items() if k != 'answer'},
                                 ensure_ascii=False), flush=True)
                print('-' * 70, flush=True)
                print(row['answer'], flush=True)
                print('-' * 70, flush=True)

    print('\n=== summary ===')
    for model in models:
        mine = [r for r in rows if r['model'] == model]
        answerable = [r for r in mine if r['expectation'] != 'absent']
        grounded = sum(r['grounded'] for r in answerable)
        right_page = sum(r['cited_expected_page'] for r in answerable)
        seconds = sorted(r['seconds'] for r in mine)
        print(f"{model:<14} grounded {grounded}/{len(answerable)}  "
              f"cited an expected page {right_page}/{len(answerable)}  "
              f"median {seconds[len(seconds) // 2]}s  max {seconds[-1]}s")
    out = Path(__file__).with_name('local-model-comparison.json')
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    print('saved', out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
