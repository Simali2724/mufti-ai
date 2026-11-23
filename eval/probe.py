"""Ask one question end-to-end and print the parts that matter for diagnosis.

Usage:
    .\.venv\Scripts\python.exe -m eval.probe "Explain Gender Equality in detail"
    .\.venv\Scripts\python.exe -m eval.probe --retrieval-only "Explain Gender Equality in detail"

`--retrieval-only` skips every answering model call, so it finishes in seconds and shows
exactly which pages reached the candidate pool and which became evidence windows. That
separates a retrieval miss from an answering or verification failure without waiting for a
local model. Nothing here feeds an expected answer to the application.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def retrieval_only(question):
    from app.agents import language_agent
    from app.retrieval.hybrid import search
    from app.retrieval.evidence import select
    from app.agents.retriever_agent import token_budget
    from app.ingestion import segment_index

    record = segment_index.active_build()
    print('segment build:', json.dumps(record) if record else 'NONE ACTIVE (page-level corpus)')
    started = time.monotonic()
    language = await language_agent.run({'user_input': question, 'language_hint': 'auto', 'history': []})
    print('language:', language['detected_language'], '| concepts:', language['matched_concepts'])
    for query in language['search_queries']:
        print(f"  variant [{query['origin']}/{query['relation']}] {query['text']}")
    candidates, report = await search(language['search_queries'])
    print('corpus mode:', report['mode'], '| corpus size:', report['corpus'])
    for row in report['queries']:
        print(f"  {row['query'][:44]!r:<48} bm25={row['bm25_pages']} dense={row['dense_pages']}")
    print('candidate pages:', [c['page_start'] for c in candidates][:30])
    windows, selection = select(candidates, token_budget=token_budget(),
                                concepts=language['matched_concepts'])
    print('window pages: ', selection['selected_pages'], '| tokens', selection['tokens'],
          '/', selection['token_budget'])
    for window in windows:
        print(f"  [{window['source_id']}] page {window['page_start']} "
              f"rel={window['relevance']} dense={window['dense_score']} lex={window['lexical_score']} "
              f"{window['relation']} spans={len(window['spans'])} tokens={window['tokens']}")
        print('      ', window['text'][:220].replace('\n', ' '))
    print('seconds:', round(time.monotonic() - started, 2))
    return {'question': question, 'candidate_pages': [c['page_start'] for c in candidates],
            'window_pages': selection['selected_pages'],
            'windows': [{'page': w['page_start'], 'relevance': w['relevance'], 'text': w['text']}
                        for w in windows]}


async def full(question, language_hint='auto'):
    from app.agents.graph import graph_context, ask
    from app.core.schemas import ChatRequest
    from app.ingestion import segment_index

    record = segment_index.active_build()
    print('segment build:', json.dumps(record) if record else 'NONE ACTIVE (page-level corpus)')
    async with graph_context() as graph:
        response = await ask(graph, ChatRequest(question=question, language_hint=language_hint,
                                                session_id=f'probe-{time.time_ns()}'))
    print('=' * 78)
    print(response.answer)
    print('=' * 78)
    print('grounded      :', response.grounded)
    print('coverage      :', response.coverage)
    print('reason_code   :', response.reason_code or '(none)')
    print('selected model:', response.selected_provider, '/', response.selected_model)
    print('answering     :', response.answering_provider, '/', response.answering_model)
    print('fallback      :', response.fallback_reason or '(none)')
    print('evidence pages:', response.evidence_pages)
    print('citation pages:', [c.page for c in response.citations])
    print('missing       :', response.missing_aspects)
    print('retrieved     :', response.retrieved_count, '| latency', response.latency_ms, 'ms')
    print('execution     :', [f"{e['task']}:{e['provider']}/{e['model']}" for e in response.execution])
    return json.loads(response.model_dump_json())


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('question')
    parser.add_argument('--retrieval-only', action='store_true')
    parser.add_argument('--language-hint', default='auto')
    parser.add_argument('--out', default='')
    # Run one probe against a different provider WITHOUT touching the user's saved
    # model-settings.json. The app itself always reads the saved preference; this only
    # overrides it for the lifetime of this process, so an evaluation can measure the cloud
    # route while the user's own choice (Ollama only) stays exactly as they left it.
    parser.add_argument('--mode', default='', choices=['', 'auto', 'anthropic', 'openai',
                                                       'gemini', 'ollama'])
    args = parser.parse_args()
    if args.mode:
        from app.llm import preferences
        saved = preferences.get_preferences()
        override = saved.model_copy(deep=True, update={'mode': args.mode})
        preferences.get_preferences = lambda: override.model_copy(deep=True)
        print('provider override for this run only:', args.mode,
              '| saved preference on disk is still:', saved.mode)
    result = (await retrieval_only(args.question) if args.retrieval_only
              else await full(args.question, args.language_hint))
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
        print('saved', args.out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
