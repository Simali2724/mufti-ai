"""Request-scoped answer traces, written locally so failures can be classified honestly.

A trace records the question, rewritten queries and variants, candidate and selected page
IDs with their scores, the evidence actually sent, the model used at each stage, timings
and the final failure class. Nothing here reads or writes credentials: provider names and
model IDs are recorded, API keys never are.
"""
import json
import re
import time
from contextvars import ContextVar
from pathlib import Path
from app.core.config import ROOT

DIAGNOSTICS_DIR = ROOT / 'data/diagnostics'
MAX_FILES = 200


override = {'dir': None}


def directory():
    """Where traces are written. Overridable so tests never touch the real trace history."""
    return Path(override['dir']) if override['dir'] else DIAGNOSTICS_DIR

# Why an answer was not produced. These are deliberately distinct: a provider outage must
# never be reported to the reader as an absence of evidence in the book.
REASONS = {
    'retrieval_unavailable': 'The search service (embeddings or vector store) failed.',
    'no_matching_passages': 'Search ran but no passage passed the relevance floor.',
    'unreadable_sources': 'The best-matching pages have unusable extracted text.',
    'provider_unavailable': 'No answering model could be reached.',
    'provider_quota_exhausted': 'Every configured cloud provider refused with a quota limit.',
    'insufficient_coverage': 'Passages were found but none directly answers the question.',
    'unsupported_claims': 'A draft was produced but no claim survived source verification.',
    'explanation_unverified': ('The book carries material on this topic, but no drafted claim '
                               'survived verification, so source excerpts are shown instead '
                               'of an explanation.'),
    'insufficient_evidence_after_search': ('Searching finished and the passages found do not '
                                           'cover the question.'),
    'extraction_problem': ('The matched pages exist but their extracted text is unreadable '
                           'legacy-font OCR noise; nothing can be quoted from them.'),
    'search_incomplete': ('The configured search budget expired before the book had been '
                          'searched enough to answer; this is not an absence of evidence.'),
    'partial_coverage': 'Part of the question is answered; the rest is not covered.',
    'needs_topic': 'The question names no subject to look up; the reader was asked which topic they mean.',
    'out_of_scope': 'The question is not about the indexed books.',
    'unsafe': 'The request was refused on safety grounds.',
}

trace_var: ContextVar[dict | None] = ContextVar('diagnostic_trace', default=None)


def start(question, language_hint='auto'):
    trace = {'question': question, 'language_hint': language_hint, 'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
             'monotonic': time.monotonic(), 'stages': [], 'retrieval': {}, 'evidence': {}, 'answer': {},
             'verification': {}, 'models': [], 'outcome': {}}
    trace_var.set(trace)
    return trace


def current():
    return trace_var.get()


def stage(name, seconds, **data):
    trace = current()
    if trace is not None:
        trace['stages'].append({'stage': name, 'seconds': round(seconds, 3), **data})


def record(section, **data):
    trace = current()
    if trace is not None:
        trace.setdefault(section, {}).update(data)


def note_model(task, provider, model, state, detail=''):
    trace = current()
    if trace is not None:
        trace['models'].append({'task': task, 'provider': provider, 'model': model, 'state': state, 'detail': detail})


def provider_failures():
    """Per-provider failure details seen in this request, for honest status reporting."""
    trace = current()
    out = {}
    for item in (trace or {}).get('models', []):
        if item['state'].startswith(('failed', 'skipped')):
            out.setdefault(item['provider'], []).append(item['detail'] or item['state'])
    return out


def quota_exhausted():
    return any('429' in detail for details in provider_failures().values() for detail in details)


class timer:
    def __init__(self, name, **data):
        self.name, self.data = name, data

    def __enter__(self):
        self.started = time.monotonic()
        return self

    def __exit__(self, *_):
        stage(self.name, time.monotonic() - self.started, **self.data)
        return False


def save(outcome=None):
    trace = current()
    if trace is None:
        return None
    trace['outcome'] = {**trace.get('outcome', {}), **(outcome or {})}
    trace['total_seconds'] = round(time.monotonic() - trace.pop('monotonic', time.monotonic()), 3)
    target = directory()
    target.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', trace['question'].lower())[:40].strip('-') or 'question'
    path = target / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}.json"
    path.write_text(json.dumps(trace, ensure_ascii=False, indent=1), encoding='utf-8')
    files = sorted(target.glob('*.json'))
    for stale in files[:-MAX_FILES]:
        stale.unlink(missing_ok=True)
    return path
