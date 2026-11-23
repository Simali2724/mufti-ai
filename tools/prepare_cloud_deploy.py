"""Prepare Mufti AI for cloud deployment.

Runs LOCALLY to build a Gemini-embedding-based index, then prepares
all files needed for a cloud deploy. The resulting cloud-index directory
is committed to the repo so the Docker container does not need Ollama.

Usage:
    .\.venv\Scripts\python.exe -u -m tools.prepare_cloud_deploy
"""
import asyncio
import json
import os
import shutil
import sys
import time

# Force Gemini embeddings
os.environ['EMBEDDING_PROVIDER'] = 'gemini'
os.environ['DEPLOY_MODE'] = 'cloud'
os.environ['LLM_PROVIDER_ORDER'] = 'gemini'

sys.stdout.reconfigure(encoding='utf-8')


async def main():
    from app.core.config import settings, INDEX, BOOKS, ROOT

    print('=' * 60)
    print('  Mufti AI — Cloud Deploy Preparation')
    print('=' * 60)
    print(f'\nEmbedding provider: {settings.embedding_provider}')
    print(f'Gemini model: {settings.gemini_embedding_model}')
    print(f'API key: {"configured" if settings.google_api_key else "MISSING!"}')

    if not settings.google_api_key:
        print('\nERROR: Set GOOGLE_API_KEY in .env first.')
        sys.exit(1)

    pdfs = list(BOOKS.glob('*.pdf'))
    print(f'Books found: {len(pdfs)}')
    for p in pdfs:
        print(f'  - {p.name} ({p.stat().st_size / 1024 / 1024:.1f} MB)')

    if not pdfs:
        print('\nERROR: No PDFs in data/books/. Add your books first.')
        sys.exit(1)

    # Destination: cloud-ready index
    cloud_dir = ROOT / 'data' / 'cloud-index'

    print(f'\n--- Step 1/4: Re-index books with Gemini embeddings ---')
    started = time.monotonic()

    from app.ingestion.indexer import ingest
    report = await ingest(force=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Ingestion took {time.monotonic() - started:.0f}s')

    print(f'\n--- Step 2/4: Build segment index ---')
    from app.ingestion import segment_index
    record = await segment_index.build(progress=print)
    print(json.dumps(record, indent=2))

    print(f'\n--- Step 3/4: Validate ---')
    validation = segment_index.validate(record['build_id'])
    print(json.dumps(validation, indent=2, ensure_ascii=False))

    if not validation['ok']:
        print('\nWARNING: Validation issues — review before deploying.')
    else:
        print('\nValidation passed!')
        segment_index.activate(record['build_id'])
        print(f'Activated build {record["build_id"]}')

    print(f'\n--- Step 4/4: Copy cloud-ready index ---')
    if cloud_dir.exists():
        shutil.rmtree(cloud_dir)
    cloud_dir.mkdir(parents=True)

    # Copy Chroma database
    src_chroma = INDEX / 'chroma'
    if src_chroma.exists():
        shutil.copytree(src_chroma, cloud_dir / 'chroma')
        print(f'  Copied chroma/')

    # Copy segments (only the active build)
    src_segments = INDEX / 'segments'
    if src_segments.exists():
        shutil.copytree(src_segments, cloud_dir / 'segments')
        print(f'  Copied segments/')

    # Copy catalog and pages
    for name in INDEX.glob('*.json'):
        shutil.copy2(name, cloud_dir / name.name)
        print(f'  Copied {name.name}')

    # Copy book metadata
    book_meta = ROOT / 'data' / 'book-metadata'
    if book_meta.exists():
        shutil.copytree(book_meta, cloud_dir / 'book-metadata')
        print(f'  Copied book-metadata/')

    # Copy trees
    src_trees = INDEX / 'trees'
    if src_trees.exists():
        shutil.copytree(src_trees, cloud_dir / 'trees')
        print(f'  Copied trees/')

    total = sum(f.stat().st_size for f in cloud_dir.rglob('*') if f.is_file())
    print(f'\nCloud index total: {total / 1024 / 1024:.1f} MB')

    print(f'\n' + '=' * 60)
    print(f'  DONE! Cloud index ready at: data/cloud-index/')
    print(f'  Total time: {time.monotonic() - started:.0f}s')
    print(f'=' * 60)
    print(f'\nNext steps:')
    print(f'  1. Update .gitignore to include data/cloud-index/')
    print(f'  2. git add + commit + push')
    print(f'  3. Deploy on Render.com')


if __name__ == '__main__':
    asyncio.run(main())
