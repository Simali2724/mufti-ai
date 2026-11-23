"""Setup check ("doctor"): is everything a new user needs in place, and if not, what to do.

Added 2026-11-17. Used by:
  * the UI guide (Help → Setup check), through GET /health/setup;
  * the command line:  .\\.venv\\Scripts\\python.exe -m app.core.setup_check   (or .\\doctor.ps1)

Every check returns a status (ok / warn / fail), what was found, and the exact fix in English
and Hinglish. Checks only READ state: nothing here starts, stops, installs or rebuilds anything,
and no API key value is ever read out (only whether one is configured).
"""
import asyncio
import json
import os
import shutil
import socket
import sys
from pathlib import Path

from app.core.config import settings, INDEX, BOOKS, ROOT


def item(check_id, label, status, detail, fix='', fix_hinglish=''):
    return {'id': check_id, 'label': label, 'status': status, 'detail': detail,
            'fix': fix, 'fix_hinglish': fix_hinglish}


def check_env():
    if (ROOT / '.env').exists():
        return item('env', 'Settings file (.env)', 'ok', '.env found.')
    return item('env', 'Settings file (.env)', 'fail', '.env is missing.',
                'Copy .env.example to .env:  Copy-Item .env.example .env',
                '.env.example ko copy karke .env banaiye:  Copy-Item .env.example .env')


def check_books():
    from app.ingestion.indexer import catalog
    pdfs = sorted(p.name for p in BOOKS.glob('*.pdf'))
    books = catalog()
    indexed = {b.get('filename') for b in books}
    new = [p for p in pdfs if p not in indexed]
    if not pdfs:
        return item('books', 'Books (PDF)', 'fail', 'No PDF in data/books/.',
                    'Put your book PDFs in D:\\mufti-ai\\data\\books\\ and index the library.',
                    'Apni kitab ki PDF D:\\mufti-ai\\data\\books\\ mein daaliye, phir library index kijiye.')
    if new:
        return item('books', 'Books (PDF)', 'warn',
                    f'{len(books)} indexed; {len(new)} new PDF(s) not indexed yet: ' + ', '.join(new[:3]),
                    'Open "My library" and click "Index library" (or run the indexer).',
                    '"My library" kholiye aur "Index library" dabaiye.')
    return item('books', 'Books (PDF)', 'ok', f'{len(books)} book(s) indexed: ' + ', '.join(pdfs[:3]))


def check_segment_index():
    from app.ingestion import segment_index
    record = segment_index.active_build()
    if record:
        return item('search_index', 'Search index', 'ok',
                    f"Active build {record.get('build_id')} ({record.get('segments', '?')} segments, "
                    f"{record.get('embedding_model')}).")
    if (INDEX / 'chunks.json').exists():
        return item('search_index', 'Search index', 'warn',
                    'Page-level index only; the finer child-segment index is not active.',
                    'See RUN_COMMANDS.md → "Checking the search index" (build, validate, activate).',
                    'RUN_COMMANDS.md mein "Checking the search index" dekhiye (build → validate → activate).')
    return item('search_index', 'Search index', 'fail', 'No search index yet.',
                'Index the library first (My library → Index library).',
                'Pehle library index kijiye (My library → Index library).')


def check_outlines():
    from app.ingestion import book_tree
    from app.ingestion.indexer import catalog
    books = catalog()
    missing = [b.get('filename', b['id']) for b in books if not book_tree.load(b['id'])]
    if not books:
        return item('outline', 'Chapter outline', 'warn', 'No books indexed yet.')
    if missing:
        return item('outline', 'Chapter outline', 'warn',
                    'No chapter outline for: ' + ', '.join(missing[:3]) + ' (chapter explorer and topic suggestions limited).',
                    'Build it:  .\\.venv\\Scripts\\python.exe -m app.ingestion.book_tree',
                    'Outline banaiye:  .\\.venv\\Scripts\\python.exe -m app.ingestion.book_tree')
    return item('outline', 'Chapter outline', 'ok', f'Outline available for all {len(books)} book(s).')


async def ollama_models():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=4, trust_env=False) as client:
            response = await client.get(settings.ollama_base_url + '/api/tags')
            response.raise_for_status()
            return True, [m.get('name', '') for m in response.json().get('models', [])]
    except Exception:
        return False, []


def _installed(name, models):
    base = name.removesuffix(':latest')
    return any(m.removesuffix(':latest') == base for m in models)


async def check_ollama():
    from app.llm.preferences import get_preferences
    # Cloud mode: Ollama not needed
    if settings.deploy_mode == 'cloud':
        return [item('ollama', 'Ollama (local AI service)', 'ok',
                      'Cloud mode — Ollama not required (Gemini embeddings used).')]
    online, models = await ollama_models()
    out = []
    if not online:
        out.append(item('ollama', 'Ollama (local AI service)', 'fail',
                        f'Not reachable at {settings.ollama_base_url}. Search needs it even in cloud mode '
                        '(the bge-m3 embeddings are local).',
                        'Start Ollama (Start menu → Ollama, or run:  ollama serve).',
                        'Ollama start kijiye (Start menu → Ollama, ya:  ollama serve). Cloud mode mein bhi search ke liye zaroori hai.'))
        return out
    out.append(item('ollama', 'Ollama (local AI service)', 'ok', f'Running, {len(models)} model(s) installed.'))
    if _installed(settings.embedding_model, models):
        out.append(item('embedding', 'Search model (embeddings)', 'ok', f'{settings.embedding_model} installed.'))
    else:
        out.append(item('embedding', 'Search model (embeddings)', 'fail', f'{settings.embedding_model} is not installed.',
                        f'Run:  ollama pull {settings.embedding_model}', f'Chalaiye:  ollama pull {settings.embedding_model}'))
    local = get_preferences().models.get('ollama') or settings.ollama_chat_model
    if _installed(local, models):
        out.append(item('local_model', 'Local answer model', 'ok', f'{local} installed (offline fallback).'))
    else:
        out.append(item('local_model', 'Local answer model', 'warn', f'{local} is not installed; no offline fallback.',
                        f'Run:  ollama pull {local}   (or choose an installed model in Models & fallback).',
                        f'Chalaiye:  ollama pull {local}   (ya Models & fallback mein installed model chuniye).'))
    return out


def check_cloud():
    from app.llm.router import has_key
    from app.llm.preferences import get_preferences
    keys = [p for p in ('gemini', 'anthropic', 'openai') if has_key(p)]
    preferences = get_preferences()
    out = []
    if keys:
        out.append(item('cloud_keys', 'Cloud AI keys', 'ok', 'Configured: ' + ', '.join(keys) + ' (values never shown).'))
    else:
        out.append(item('cloud_keys', 'Cloud AI keys', 'warn',
                        'No cloud key: answers come from the small local model (slow on a 2 GB GPU, not fact-checked).',
                        'For fast, fact-checked answers add GOOGLE_API_KEY (or ANTHROPIC_API_KEY / OPENAI_API_KEY) to .env and restart.',
                        'Tez aur fact-checked jawab ke liye .env mein GOOGLE_API_KEY (ya ANTHROPIC/OPENAI key) daaliye aur restart kijiye.'))
    mode = preferences.mode
    if mode not in ('auto', 'ollama') and not has_key(mode):
        out.append(item('mode', 'Answering mode', 'warn', f'Mode "{mode}" is selected but has no key, so it is skipped.',
                        'Open Models & fallback and choose Auto or a provider with a key.',
                        'Models & fallback kholiye aur Auto ya key wala provider chuniye.'))
    else:
        out.append(item('mode', 'Answering mode', 'ok', f'Mode: {mode}; models: '
                        + ', '.join(f'{k}={v}' for k, v in preferences.models.items())))
    return out


def check_ocr():
    binary = shutil.which('tesseract') or next(
        (str(p) for p in [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Tesseract-OCR/tesseract.exe']
         if p.exists()), '')
    if binary:
        return item('ocr', 'OCR (Tesseract, for scanned books)', 'ok', 'Tesseract found.')
    return item('ocr', 'OCR (Tesseract, for scanned books)', 'warn',
                'Tesseract not found. Already-indexed books still work; NEW scanned books cannot be indexed.',
                'Install Tesseract (UB Mannheim build) with the urd/eng language packs. See README → OCR.',
                'Naye scanned books ke liye Tesseract (UB Mannheim) urd/eng packs ke saath install kijiye.')


def check_storage():
    from app.core.storage import storage_status
    status = storage_status(INDEX)
    if status in ('ok', 'not_initialized'):
        return item('storage', 'Conversation storage', 'ok',
                    'Ready.' if status == 'ok' else 'Will be created on the first question.')
    return item('storage', 'Conversation storage', 'fail', 'sessions.sqlite cannot be read.',
                'Check that the D: drive is connected and healthy (RUN_COMMANDS.md → "If the D: drive disconnects").',
                'D: drive connected hai ya nahi check kijiye (RUN_COMMANDS.md → "If the D: drive disconnects").')


def port_open(port=None):
    try:
        with socket.create_connection(('127.0.0.1', port or settings.port), timeout=1):
            return True
    except OSError:
        return False


async def run_checks(include_server=False):
    checks = [check_env(), check_books(), check_segment_index(), check_outlines()]
    checks += await check_ollama()
    checks += check_cloud()
    checks += [check_ocr(), check_storage()]
    if include_server:
        if port_open():
            checks.append(item('server', 'Mufti AI server', 'ok', f'Listening on http://localhost:{settings.port}'))
        else:
            checks.append(item('server', 'Mufti AI server', 'warn', f'Nothing listening on port {settings.port}.',
                               'Start it:  .\\start.ps1', 'Server start kijiye:  .\\start.ps1'))
    worst = 'fail' if any(c['status'] == 'fail' for c in checks) else (
        'warn' if any(c['status'] == 'warn' for c in checks) else 'ok')
    return {'status': worst, 'checks': checks}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    report = asyncio.run(run_checks(include_server=True))
    if '--json' in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    icon = {'ok': '[ OK ]', 'warn': '[WARN]', 'fail': '[FAIL]'}
    print('Mufti AI setup check\n' + '=' * 60)
    for check in report['checks']:
        print(f"{icon[check['status']]} {check['label']}: {check['detail']}")
        if check['status'] != 'ok' and check['fix']:
            print(f"        Fix: {check['fix']}")
            print(f"        Hal: {check['fix_hinglish']}")
    print('=' * 60)
    print({'ok': 'Everything is ready. Open http://localhost:786',
           'warn': 'Usable, with the warnings above.',
           'fail': 'Fix the [FAIL] items above first.'}[report['status']])


if __name__ == '__main__':
    main()
