"""Refresh the machine-written state block at the top of Handsover.md.

Why: the user asked that the handover always be current "when the limit runs out or the work is
complete". An AI session can end without warning (usage limit, context limit, laptop shutdown),
so the FACTS part of the handover is regenerated automatically:

  * by the Claude Code hooks in .claude/settings.json (Stop = every finished turn,
    PreCompact = just before the context is compacted), and
  * by hand:   .\\.venv\\Scripts\\python.exe tools\\handover_snapshot.py [--tests]

It rewrites ONLY the text between <!-- AUTO-SNAPSHOT:START --> and <!-- AUTO-SNAPSHOT:END -->.
The narrative sections (what was done, why, what next) are still written by the AI/human — see
the "Handover protocol" in AGENTS.md.

Standard library only, read-only except for that one block, never prints or stores secrets
(only whether a key is configured), finishes in about a second without --tests.
"""
import argparse
import datetime as dt
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOVER = ROOT / 'Handsover.md'
START, END = '<!-- AUTO-SNAPSHOT:START -->', '<!-- AUTO-SNAPSHOT:END -->'
SOURCE_DIRS = ['app', 'frontend', 'tests', 'mcp_server', 'tools', 'eval']
SKIP_PARTS = {'__pycache__', '.venv', 'backups', 'data', '.pytest_cache'}


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return default


def listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5):
            return True
    except OSError:
        return False


def env_keys():
    """Names of configured cloud keys. The values are never read into the output."""
    configured = []
    try:
        for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
            name, _, value = line.partition('=')
            if name.strip() in ('GOOGLE_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY') and value.strip():
                configured.append(name.strip())
    except OSError:
        pass
    return configured


def recent_files(hours=48, limit=15):
    cutoff = dt.datetime.now().timestamp() - hours * 3600
    files = []
    for folder in SOURCE_DIRS:
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and not SKIP_PARTS & set(path.parts) and path.suffix in {'.py', '.js', '.css', '.html', '.jsonl'}:
                if path.stat().st_mtime >= cutoff:
                    files.append(path)
    files += [p for p in ROOT.glob('*.md') if p.stat().st_mtime >= cutoff]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [(p.relative_to(ROOT).as_posix(), dt.datetime.fromtimestamp(p.stat().st_mtime)) for p in files[:limit]]


def newest(pattern, limit=3):
    paths = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return [(p.relative_to(ROOT).as_posix(), dt.datetime.fromtimestamp(p.stat().st_mtime)) for p in paths[:limit]]


def open_tasks(limit=10):
    try:
        lines = (ROOT / 'TASKS.md').read_text(encoding='utf-8').splitlines()
    except OSError:
        return 0, []
    items = [re.sub(r'^\s*-\s*\[ \]\s*', '', l).strip() for l in lines if re.match(r'^\s*-\s*\[ \]', l)]
    return len(items), items[-limit:]


def count_tests():
    total = 0
    for path in (ROOT / 'tests').glob('test_*.py'):
        total += len(re.findall(r'^(?:async )?def test_', path.read_text(encoding='utf-8'), re.M))
    return total


def run_tests():
    python = ROOT / '.venv' / 'Scripts' / 'python.exe'
    if not python.exists():
        python = Path(sys.executable)
    try:
        out = subprocess.run([str(python), '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], cwd=ROOT,
                             capture_output=True, text=True, timeout=900)
        tail = [l for l in out.stdout.strip().splitlines() if l.strip()][-1:]
        return tail[0] if tail else f'pytest exited {out.returncode}'
    except Exception as exc:
        return f'not run ({type(exc).__name__})'


def snapshot(with_tests=False):
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    catalog = read_json(ROOT / 'data/index/catalog.json', [])
    active = read_json(ROOT / 'data/index/segments/active.json', {})
    prefs = read_json(ROOT / 'model-settings.json', {})
    task_count, tasks = open_tasks()
    lines = [START,
             '## Auto-snapshot (machine-written — do not edit by hand)',
             f'_Refreshed {now} by `tools/handover_snapshot.py`. Facts only; the narrative is in the sections below._',
             '',
             '| Item | State |', '|---|---|',
             f"| App server `http://localhost:786` | {'listening' if listening(786) else 'not running'} |",
             f"| Ollama `:11434` (needed for search embeddings) | {'listening' if listening(11434) else 'not running'} |",
             f"| Books indexed | {len(catalog)}: " + '; '.join(
                 f"{b.get('filename')} ({b.get('pages')} p, {b.get('chunks')} chunks{'' if b.get('complete') else ', INCOMPLETE'})"
                 for b in catalog) + ' |',
             f"| Active segment build | {active.get('build_id', 'none')} ({active.get('segments', '?')} segments, {active.get('embedding_model', '?')}) |",
             f"| Saved answering mode | {prefs.get('mode', '?')} · " + ', '.join(f'{k}={v}' for k, v in (prefs.get('models') or {}).items()) + ' |',
             f"| Cloud keys configured (names only) | {', '.join(env_keys()) or 'none'} |",
             f'| Offline test functions | {count_tests()} in tests/test_*.py |']
    if with_tests:
        lines.append(f'| Offline suite result (this snapshot) | {run_tests()} |')
    lines.append(f'| Open TASKS.md items | {task_count} |')
    lines += ['', '**Recently changed source/docs (48 h):** ' + (', '.join(
        f'`{p}` ({t:%m-%d %H:%M})' for p, t in recent_files()) or 'none')]
    lines += ['', '**Newest eval results:** ' + (', '.join(f'`{p}` ({t:%m-%d %H:%M})' for p, t in newest('eval/*.json')) or 'none')]
    lines += ['', '**Newest request trace:** ' + (', '.join(f'`{p}`' for p, _ in newest('data/diagnostics/*.json', 1)) or 'none')]
    lines += ['', '**Newest backup:** ' + (', '.join(f'`{p}`' for p, _ in newest('backups/*', 1)) or 'none')]
    if tasks:
        lines += ['', '**Last open items in TASKS.md:**'] + [f'- [ ] {t}' for t in tasks]
    lines.append(END)
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--tests', action='store_true', help='also run the offline pytest suite (~20 s)')
    parser.add_argument('--quiet', action='store_true', help='print nothing (for hooks)')
    parser.add_argument('--print', action='store_true', help='print the block instead of writing it')
    args = parser.parse_args()
    block = snapshot(args.tests)
    if args.print:
        sys.stdout.reconfigure(encoding='utf-8')
        print(block)
        return
    text = HANDOVER.read_text(encoding='utf-8') if HANDOVER.exists() else '# AI handover — start here\n'
    if START in text and END in text:
        text = text[:text.index(START)] + block + text[text.index(END) + len(END):]
    else:
        head, _, rest = text.partition('\n')
        text = head + '\n\n' + block + '\n' + rest
    HANDOVER.write_text(text, encoding='utf-8')
    if not args.quiet:
        print(f'Handsover.md auto-snapshot refreshed ({len(block.splitlines())} lines).')


if __name__ == '__main__':
    main()
