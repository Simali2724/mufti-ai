"""Targeted repair of individual rejected claims, before any of them is abandoned.

The brief is explicit: "Repair a specific rejected claim using its evidence and feedback
before abandoning it. Keep independently supported claims; do not reject an entire answer
because one claim failed." Until this node existed the pipeline had only one recovery route,
`expand`, which re-searched the book and redrafted the WHOLE answer - expensive, and useless
for the failure actually measured on this book, where retrieval and evidence were already
right and a single sentence was defective.

Two repair routes, cheapest first:

1. Deterministic attribution. When the only defect is that a claim drawn from a quoted
   passage does not name the writer the book credits, the code already knows the names from
   the book's own citation line. It writes them in. Nothing else about the claim changes and
   the repaired sentence is still verified afterwards, so this adds attribution, it does not
   add support. Measured on this machine this costs 0 s against 60-300 s for a model call.

2. Model redraft. For the remaining repairable defects the model is given the claim, its own
   verbatim span and the exact rejection reason, and is asked to rewrite that ONE sentence
   from that ONE span. The evidence is fixed: repair may change the wording, never the span
   it rests on.

A claim rejected for resting on the wrong concept's span, for citing nothing, or for citing
a span that does not exist is NOT repairable here. There is nothing in its evidence to
rewrite, and inventing a different source for it is the fabrication the guards exist to stop.
"""
import json
import time
from app.core import diagnostics
from app.core.config import settings
from app.core.language import ATTRIBUTION_PREFIX, ATTRIBUTION_JOIN
from app.llm.prompts import REPAIR_RULES
from app.llm.router import get_chat_model
from app.agents.verifier_agent import (diagnose, concept_guard, quoted_attributions, terminate,
                                       REPAIRABLE_CODES)

# Defects whose evidence is sound and whose sentence can be rewritten from the same span.
REPAIRABLE = REPAIRABLE_CODES
# Defects that are repairable by code alone, with no model call.
DETERMINISTIC = {'attribution'}


def attribute(text, names, language):
    """Prefix a claim with the writers the book credits for the span it rests on."""
    joined = ATTRIBUTION_JOIN.get(language, ' and ').join(names)
    template = ATTRIBUTION_PREFIX.get(language, ATTRIBUTION_PREFIX['English'])
    return template.format(names=joined, claim=text.strip())


def deterministic_repair(claim, window, language, guard):
    """Repair an attribution-only defect in code. Returns the fixed claim, or None."""
    names = quoted_attributions(window['text'])
    if not names:
        return None
    repaired = {**claim, 'text': attribute(claim['text'], names, language), 'repair': 'attribution'}
    code, _ = diagnose(repaired, window, language, guard)
    return repaired if not code else None


def repairable(rejected):
    return [claim for claim in rejected if claim.get('code') in REPAIRABLE]


async def model_repair(question, language, items, windows):
    """One call that rewrites several rejected claims, each from its own unchanged span."""
    by_id = {w['source_id']: w for w in windows}
    payload = {'question': question, 'reply_language': language, 'claims': []}
    for claim in items:
        window = by_id.get(claim.get('source_id'))
        if window is None:
            continue
        entry = {'claim_id': claim['claim_id'], 'rejected_claim': claim.get('text', ''),
                 'why_it_was_rejected': claim.get('reason', ''),
                 'source_pdf_page': claim.get('page'), 'source_span': claim.get('support', '')}
        names = quoted_attributions(window['text'])
        if names:
            entry['must_credit_these_writers'] = names
        payload['claims'].append(entry)
    if not payload['claims']:
        return {}
    result, provider = await get_chat_model('repair').invoke(
        REPAIR_RULES, json.dumps(payload, ensure_ascii=False), True)
    rewritten = {}
    for row in (result.get('claims') or []) if isinstance(result, dict) else []:
        if isinstance(row, dict) and isinstance(row.get('claim_id'), int) and str(row.get('text', '')).strip():
            rewritten[row['claim_id']] = str(row['text'])[:700]
    return {'texts': rewritten, 'provider': provider}


def reinstate(draft, claims):
    """Put repaired claims back into their own sections, keeping the verified ones."""
    sections = draft.get('sections') or []
    by_heading = {str(s.get('heading', '')): s for s in sections}
    for claim in claims:
        heading = str(claim.get('section_heading') or '')
        section = by_heading.get(heading)
        if section is None:
            section = {'heading': heading, 'claims': []}
            by_heading[heading] = section
            sections.append(section)
        section['claims'].append(claim)
    draft['sections'] = [s for s in sections if s.get('claims')]
    draft['claims'] = [c for s in draft['sections'] for c in s['claims']]
    return draft


async def run(state):
    started = time.monotonic()
    report = state.get('verification_report', {}) or {}
    rejected = repairable(report.get('rejected_claims') or [])
    draft = state.get('draft_answer', {}) or {}
    windows = state.get('evidence_windows') or []
    by_id = {w['source_id']: w for w in windows}
    language = state['detected_language']
    guard = concept_guard(state.get('matched_concepts'))
    rounds = state.get('repair_rounds', 0) + 1
    if not rejected:
        diagnostics.record('repair', skipped='no repairable claim', rounds=rounds)
        return {'repair_rounds': rounds}

    fixed, remaining = [], []
    for claim in rejected[:settings.repair_max_claims]:
        window = by_id.get(claim.get('source_id'))
        if window is None:
            continue
        repaired = (deterministic_repair(claim, window, language, guard)
                    if claim['code'] in DETERMINISTIC else None)
        if repaired is not None:
            fixed.append(repaired)
        else:
            remaining.append(claim)

    model_used, failures = '', []
    if remaining and settings.repair_with_model:
        try:
            result = await model_repair(state['user_input'], language, remaining, windows)
            model_used = result.get('provider', '')
            for claim in remaining:
                text = (result.get('texts') or {}).get(claim['claim_id'])
                if not text:
                    continue
                candidate = {**claim, 'text': terminate(text, language), 'repair': 'model'}
                window = by_id[claim['source_id']]
                code, reason = diagnose(candidate, window, language, guard)
                if not code:
                    fixed.append(candidate)
                elif code in DETERMINISTIC:
                    deterministic = deterministic_repair(candidate, window, language, guard)
                    if deterministic is not None:
                        fixed.append({**deterministic, 'repair': 'model+attribution'})
                    else:
                        failures.append(reason)
                else:
                    failures.append(reason)
        except Exception as exc:
            diagnostics.record('repair', failure=type(exc).__name__)
            failures.append(type(exc).__name__)

    for claim in fixed:
        claim.pop('reason', None)
        claim.pop('code', None)
        claim.pop('verified', None)
    diagnostics.stage('repair', time.monotonic() - started)
    diagnostics.record('repair', rounds=rounds, candidates=len(rejected),
                       deterministic=sum(c['repair'] == 'attribution' for c in fixed),
                       by_model=sum(c['repair'] != 'attribution' for c in fixed),
                       still_failing=failures[:6], provider=model_used)
    if not fixed:
        return {'repair_rounds': rounds}
    return {'draft_answer': reinstate(draft, fixed), 'repair_rounds': rounds, 'repaired': True}
