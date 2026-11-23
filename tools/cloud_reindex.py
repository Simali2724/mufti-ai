"""Cloud re-indexing: rebuild the entire search index with Gemini embeddings.

Run once after deploying to a cloud host that has no Ollama. Requires GOOGLE_API_KEY.
Usage:
    python -m tools.cloud_reindex
"""
import asyncio
import json
import sys
import os

# Force cloud settings before importing anything
os.environ.setdefault('EMBEDDING_PROVIDER', 'gemini')
os.environ.setdefault('DEPLOY_MODE', 'cloud')

sys.stdout.reconfigure(encoding='utf-8')


async def main():
    from app.ingestion.indexer import ingest
    from app.ingestion import segment_index
    from app.core.config import settings

    print(f'=== Cloud Re-Index ===')
    print(f'Embedding provider: {settings.embedding_provider}')
    print(f'Gemini model: {settings.gemini_embedding_model}')
    print(f'API key set: {"yes" if settings.google_api_key else "NO — set GOOGLE_API_KEY!"}')
    print()

    if not settings.google_api_key:
        print('ERROR: GOOGLE_API_KEY is required. Set it in .env or as an environment variable.')
        sys.exit(1)

    # Step 1: Re-ingest all books with Gemini embeddings
    print('--- Step 1: Re-ingesting books with Gemini embeddings ---')
    report = await ingest(force=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print()

    # Step 2: Rebuild segment index
    print('--- Step 2: Building segment index ---')
    record = await segment_index.build(progress=print)
    print(json.dumps(record, indent=2))
    print()

    # Step 3: Validate
    print('--- Step 3: Validating ---')
    validation = segment_index.validate(record['build_id'])
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    print()

    if validation['ok']:
        # Step 4: Activate
        print('--- Step 4: Activating ---')
        activated = segment_index.activate(record['build_id'])
        print(json.dumps(activated, indent=2))
        print()
        print('SUCCESS: Cloud index ready!')
    else:
        print('WARNING: Validation issues found. Review before activating.')
        print('To activate manually: python -m app.ingestion.segment_index activate --build-id', record['build_id'])


if __name__ == '__main__':
    asyncio.run(main())
