# REPAIR_PROMPT.md — fix anything broken in Mufti AI

**How to use this file.** Part 1 is a ready prompt: copy it into any AI (Claude Code, ChatGPT,
Gemini, Cursor…), fill in the SYMPTOM, and let it work. Part 2 is a triage table of every failure
seen so far, with the cause and the file to look at. Part 3 is the debugging toolkit. Everything
below "HISTORY" is the original 2026-11-12 → 2026-11-16 repair brief, kept for its measurements.

---

## Part 1 — Copy-paste repair prompt

```text
You are repairing Mufti AI in D:\mufti-ai (Windows; FastAPI + LangGraph; app at http://localhost:786).
Before changing anything read: AGENTS.md, Handsover.md (auto-snapshot + CURRENT STATE), TASKS.md,
Rules.md, and REPAIR_PROMPT.md Part 2 (known failures).

SYMPTOM (what the user saw, exact question, language, time):
<paste here, e.g. "Hinglish question 'Hijrat ke baad ...' answered 'not in the book' at 14:20">

Method — do these in order and write down each result:
1. Environment first: run .\doctor.ps1. Check the D: drive, Ollama on :11434, the server on :786.
   A service problem is not an answer problem.
2. Find the request trace: newest data/diagnostics/*.json matching the question. Read stages,
   retrieval (candidate pages + scores), evidence (selected windows), models (which model ran,
   failures, timeouts, 429), explain/audit, outcome.reason_code.
3. Locate the failing stage: language → router → retrieve → evidence → explain → audit → formatter.
   Confirm by reading the actual book page (GET /books/{id}/pages/{page}) — is the answer really there?
4. Reproduce with ONE live call (Gemini quota is ~20/day/model):
   .\.venv\Scripts\python.exe -u -m eval.probe "<question>" --mode gemini
   or reproduce offline with a mocked test (see tests/test_explain.py FakeModel).
5. Fix the root cause in the right layer (ADD_FEATURE.md Part B). Back up files first to
   backups/<fix-name>-<yyyymmdd>/. Add a regression test that fails before and passes after.
6. Never "fix" by weakening grounding: no relaxing AUDIT_RULES / citation checks / readability
   filters, no tuning to benchmark expectations, no deleting or rebuilding data/index.
7. Verify: pytest -q (all pass), node --check frontend\app.js, the live question again,
   and 2-3 neighbouring benchmark cases (eval.explain_eval --ids ...) so nothing else broke.
8. Hand over: Handsover.md CURRENT STATE (symptom → cause → fix → evidence → not done),
   TASKS.md, VERIFICATION.md, and add the failure to REPAIR_PROMPT.md Part 2.
Answer the user in simple Hinglish: what was wrong, what you changed, how you checked it.
```

## Part 2 — Triage table (symptom → likely cause → where to look)

| Symptom | Likely cause | Look at / fix |
|---|---|---|
| "Search service failed" / `retrieval_unavailable` | Ollama not running or bge-m3 missing | `.\doctor.ps1`; start Ollama; `ollama pull bge-m3` |
| `provider_quota_exhausted`, "quota or rate limit" | Gemini free tier (≈20/day/model) used up | trace `models` shows 429; wait for reset, other key, `config.yaml` `gemini_alternates` |
| Answer takes 2-4 minutes, then arrives from another model | Primary Gemini model stalled | trace `models`: `ReadTimeout`; `stream_read_timeout` (60 s, 2026-11-17) in `config.yaml` / `providers.py` |
| Very slow answers, no cloud | only local qwen3:1.7b on 2 GB GPU | add a cloud key; use **Short** style; Rules.md 15 |
| "Not in the book" but the page has it | retrieval missed (Hinglish wording, OCR noise) or model said `<<none>>` | trace `retrieval.candidate_scores`, `evidence.windows`; `query_expansion.py`, `concept-lexicon.json` (reviewed edits only, Rules.md 18) |
| Wrong/unrelated "related passages" | relatedness thresholds | `formatter.truly_related`, model-chosen `<<none: n>>` |
| Fact in answer not in the book | audit skipped (local model / timeout) or audit miss | badge says "not independently fact-checked"? `explain_agent.audit`, `AUDIT_RULES` (strengthen only, with a negative example) |
| Quoted Western writer's view stated as the book's view | attribution | `explain_agent.quoted_writers`, `EXPLAIN_RULES` ATTRIBUTION, Rules.md 17 |
| Hindi answer in Urdu script | lite model script mixing | `explain_agent.wrong_script_share` (one regeneration) |
| Garbled text shown as a quotation | OCR noise passed the filter | `evidence.readable`, `legible_pieces`; reason `extraction_problem` |
| Same page cited twice | two passages of one page | `explain_agent.page_aliases` |
| `<<next:` / `<<full>>` visible in the UI | marker not stripped | server: `suggest.split_followups` before `split_marker`; UI: `stripMarkers()` + `tests/ui_markdown.test.js` |
| Chapter focus ignored / "whole library was searched" | nothing in scope matched (by design) or wrong page range | response `scope.applied`; `retriever_agent.SCOPE_MIN_CANDIDATES`; outline pages in `data/index/trees/` |
| No follow-up chips | local model (outline fallback only) or no outline for that book | `suggest.from_outline`; build tree: `python -m app.ingestion.book_tree` |
| Previous turn's setting leaks into the next | per-turn key not reset in `_ask()` initial state | `graph._ask()` (see ADD_FEATURE.md "State contract") |
| Mic keeps recording / sends by itself | old mic code (before 2026-11-17 (2)) | `app.js` voice state machine; `/transcribe` must never call `ask`; `tests/test_voice.py` |
| Tour arrow points at the wrong place | layout changed after placement, or headless-Chrome viewport quirk | `tour.js` re-measures every 300 ms; verify in a real browser (headless offsets the sticky composer ~100 px) |
| Directions in the wrong language | `localStorage['mufti-ui-lang']` | 🌐 button, `?lang=English`; `tour.js` `T` |
| Answer shows "Sources linked · not fact-checked" while Gemini works | audit schema rejected (HTTP 400 "too many states") or strong audit timing out | trace `models`: `audit_strong … 400`; keep schemas unbounded (`structured.py`); `strong_audit_timeout`, `STRONG_AUDIT_CHUNK` |
| After one failed audit, the next question goes to the local model | a failing task tripped the provider breaker | `router._route`: `only_preferred` tasks must not call `breaker.fail/trip` (`tests/test_accuracy_guards.py`) |
| UI blank / buttons dead | JS error | `node --check frontend\app.js`; browser console |
| Server won't start / `sqlite` errors | D: drive I/O problem or locked DB | RUN_COMMANDS.md "If the D: drive disconnects"; never delete `sessions.sqlite` |
| Eval numbers garbage / Ollama wedged | eval and server both on Ollama | stop one (Memory.md "Do not run the server and a benchmark…") |

## Part 3 — Toolkit

```powershell
.\doctor.ps1                                                    # environment, with fixes
Get-ChildItem data\diagnostics | Sort-Object LastWriteTime | Select-Object -Last 5   # newest traces
.\.venv\Scripts\python.exe -u -m eval.probe "<question>" --mode gemini              # one live run
.\.venv\Scripts\python.exe -u -m eval.explain_eval --mode gemini --ids cm-en-3,ge-ur-1   # chosen cases
curl.exe -s http://127.0.0.1:786/books/<book_id>/pages/<page>   # what the page really says
.\.venv\Scripts\python.exe tools\handover_snapshot.py --tests   # refresh handover facts + run suite
```

---

# HISTORY — original repair brief (2026-11-12 … 2026-11-16)

## Mufti AI: repair book-answer coverage

Work in D:\mufti-ai. Source PDF: D:\Muqaddima-Seerat-ur-Rasool-1_1.pdf. Keep the app on http://localhost:786. Read applicable AGENTS.md and Handsover.md, Memory.md, Architecture.md, PRD.md, Desgin.md, Rules.md, TASKS.md and VERIFICATION.md. Preserve the original PDF, existing index, reviewed metadata, conversations, provider selections and secrets. Back up changed files; never expose .env. Do not run old scaffold scripts.

## Objective

Implement reliable answers to questions supported by the uploaded book, in English, Urdu, Hindi and Hinglish. A broad question must receive a clearly scoped partial answer when the book supports only part of it. Do not invent the rest. This is an implementation task: diagnose, fix, run, inspect real results and update the handover, not just change a system prompt.

## Confirmed findings

- The failure is `Explain Gender Equality in detail`. The screenshot shows a rejected/not-found answer attempted with Ollama llama3.2:3b while Gemini was selected. Inspect current request traces to establish the actual fallback cause; do not assume it.
- Visually checked physical PDF page 50 contains explicit gender-equality discussion, including quotations attributed to Ronald Inglehart and Pippa Norris. Preserve attribution: their quoted views are not automatically the author's own conclusions.
- Physical PDF page 257 includes `No Gender Discrimination in Adult Franchise`. Interpret this within its surrounding section, not as a complete treatment of all gender-related questions.
- Both pages are already present in the index. These are candidate relevant sources, not a hardcoded answer map. Other pages need review before using them as benchmark ground truth.
- app/agents/answer_agent.py only passes the first three passages as at most eight 25-word fragments each, then limits the answer to two claims. app/llm/structured.py enforces the same small output. Full paragraph context is lost.
- app/agents/verifier_agent.py uses an all-or-nothing check; a generated answer can also be incorrectly approved. eval/rejected-book-quality-example.json is a known false positive, not a passing result.
- Existing 109 passing tests and the successful author/page-51 cases do not prove broad book coverage.

## Implement these changes

1. Reproduce the exact failure and record the question, rewritten queries, candidate and selected page IDs, scores, context sent, actual model at each stage, timings and rejection reason. Keep diagnostic text local and omit secrets. Separate retrieval failure, OCR failure, insufficient coverage, provider failure and unsupported claims.

2. Audit page extraction against rendered PDF pages. Keep raw OCR, corrected text and correction provenance separately. Repair low-quality passages without silently inventing text. Preserve physical PDF page IDs and printed page labels separately. Use paragraph/heading-aware child chunks with overlap for search, and fetch their parent paragraphs and relevant neighboring context for answering. Stage any replacement index separately; validate it before switching, retaining rollback. Changing the embedding model requires a complete compatible re-index.

3. Improve English/Urdu/Hinglish retrieval using the original question plus controlled translations and variants. Use BM25 and existing bge-m3 embeddings with fusion; preserve lexical hits. For this case inspect variants such as gender equality, equality between men and women, صنفی مساوات and عورت اور مرد کی برابری, without treating different concepts as identical. Start by evaluating 20–40 candidates and 6–10 diverse evidence windows; tune against measured recall and the actual model context budget. Preserve attribution and avoid duplicate passages. Use a second search for missing subtopics before concluding there is no answer. Evaluate a multilingual reranker only if it improves measured quality within this machine's constraints.

4. Pass coherent paragraphs to the answer model. Keep display quote length separate from the evidence context budget: do not restrict understanding to isolated 25-word fragments. Replace the two-claim ceiling with structured, evidence-sized sections for detailed questions. Update the output schema, token budgets, parser, formatter, citations and UI together. Fit context/output to the selected model and hardware; do not assume this small GPU can handle arbitrary context lengths.

5. Support full, partial and not-found coverage explicitly. Answer the supported aspects first, state missing aspects and show relevant sources. For a broad gender-equality question, explain only the book's supported treatment and identify its limits. Related excerpts may be shown separately as related material when they do not support a direct answer. Never present them as a verified answer. Never fill gaps from model memory or the web in book-only mode.

6. Verify individual claims against complete supporting source spans, preserving subject, attribution and translation. Remove or repair unsupported claims while keeping independent supported claims. A same-model approval or an exact quote match alone is not proof of entailment. Do not weaken verification to improve answer rate. Support claim-to-source mappings, clickable PDF pages and clear OCR/correction provenance. Ensure a longer answer remains fully cited.

7. Show the selected model, actual running model, answering model and fallback reason distinctly. Replace misleading `Ready` labels when only a key is configured. Keep the user's provider order and Ollama fallback. Quota exhaustion or embedding-service failure must not be described as absence of book evidence. Avoid spending repeated model calls classifying obvious book questions; measure accuracy before simplifying stages.

8. Build a human-reviewed benchmark of at least 30–50 questions across sections and languages, including paraphrases, broad questions, partial coverage and truly absent topics. Include the exact gender-equality question and variants, the author question and the page-51 piety question. Inspect source pages before assigning expected answers. Measure relevant-page recall, false refusals on answerable questions, unsupported claims, citation correctness and latency. Compare before/after results. Keep some held-out questions and never hardcode benchmark answers. Report failures honestly; unit tests alone are insufficient.

## Completion and handover

Run the regression suite and real book queries. Manually inspect the final gender-equality response against the actual PDF and its attribution. Test the configured cloud route and Ollama fallback, reporting whether failures were simulated or real. Verify the browser UI and save evidence. Leave the app running on port 786. Update Architecture.md, Desgin.md, Memory.md, PRD.md, Rules.md, TASKS.md, VERIFICATION.md, RUN_COMMANDS.md and Handsover.md with changed files, commands, observed results, remaining weaknesses and the exact next step if interrupted. Do not claim universal coverage or completion while measured failures remain unresolved.


## Implementation status — 2026-11-12, after an unplanned laptop shutdown

The shutdown happened at about 00:04 on 2026-11-12, during the first benchmark run. Nothing
below is a claim of coverage; the measured numbers are recorded in Handsover.md as they are
produced. Status is per numbered step above.

1. **Reproduce and trace — done.** `app/core/diagnostics.py` records a per-request trace
   (rewritten queries, candidates, selected windows, model at each stage, timings, rejection
   reasons) to `data/diagnostics/<timestamp>-<question>.json`. Retrieval failure, insufficient
   coverage, provider failure and unsupported claims are separate reason codes. Secrets are
   not written to the trace.
   **Not yet done: no real end-to-end trace of the failing question has been captured.** Every
   file currently in `data/diagnostics/` was produced by the offline suite with mocked models
   (0 models recorded, sub-second totals, empty `stages`), so none of them is evidence about
   live behaviour. The mocked gender-equality case does return `partial_coverage` citing page
   257 while reviewed page 50 is absent, which is a lead, not a measurement. Capture a real
   trace once the segment index is active. Separately, the test suite writes into the real
   `data/diagnostics/` directory; it should write to a temporary path instead.

2. **Extraction audit and paragraph-aware child chunks — code done, index NOT active.**
   `app/ingestion/segments.py` and `app/ingestion/segment_index.py` are new. Raw OCR,
   reviewed correction, correction provenance, physical page id and printed page label are
   kept as separate fields. The audit covers all 689 pages and flags 181:
   28 empty, 91 fragmented tokens, 55 no English layer, 10 control characters, 5 very short.
   Saved to `data/index/extraction-audit.json` and served by `GET /admin/books/{id}/extraction-audit`.
   The staged build `data/index/segments/20261111-234724/` was interrupted by the shutdown: it
   has a partial `chroma/` directory but no `segments.json` and no `active.json`. With no
   active build `load_segments()` returns `[]`, so retrieval is still running on page-level
   chunks and the child-segment layer contributes nothing. **This is the main unfinished
   item.** Rebuild, validate and activate:
   ```powershell
   .\.venv\Scripts\python.exe -m app.ingestion.segment_index build
   .\.venv\Scripts\python.exe -m app.ingestion.segment_index validate --build-id <id>
   .\.venv\Scripts\python.exe -m app.ingestion.segment_index activate --build-id <id>
   ```
   The live page index is never written by this path, and `rollback` returns to the previous
   build or deactivates segments entirely. A changed embedding model invalidates every build.

3. **Multilingual retrieval variants and fusion — code done, not yet measured.**
   `data/concept-lexicon.json` plus `app/agents/language_agent.py` produce the original
   question and controlled variants; `app/retrieval/hybrid.py` fuses BM25 and bge-m3 and keeps
   lexical hits. Recall is being measured by the benchmark, not asserted here.

4. **Paragraph context to the answering model — done.** `app/retrieval/evidence.py` builds
   whole-parent-paragraph windows with neighbour extension, numbered verbatim spans, a token
   budget sized per model, and a display quote kept separate from the verified support. The
   three-passage and two-claim ceilings are gone; output is sectioned.

5. **Full, partial and not-found coverage — done.** `coverage` and `missing_aspects` on the
   response schema, surfaced by the formatter and the frontend. Related-but-not-supporting
   excerpts are shown as related material, never as a verified answer.

6. **Per-claim verification — done.** `app/agents/verifier_agent.py` judges each claim against
   its own complete span, with a code-checkable structural pass first, then one model verdict
   per claim covering entailment, attribution and whether it answers the question. Unsupported
   claims are pruned and supported ones survive. Verification was not weakened.

7. **Honest model and provider status — done.** `provider_state` in `app/api/routes_models.py`
   distinguishes no key, key configured but unused, last call failed, quota or rate limit
   reached, and paused after failures. The misleading `Ready` label is gone. Quota exhaustion
   and embedding failure are reported as service failures, never as absence of book evidence.
   Regression tests for this were added on 2026-11-12.

8. **Human-reviewed benchmark — written, measurement in progress.** 48 reviewed cases in
   `eval/book_benchmark.jsonl` across sections and English/Urdu/Hindi/Hinglish, including the
   exact gender-equality question and variants, the author question, the page-51 piety
   question, broad questions, partial-coverage questions, absent topics and hold-outs. No
   expected answer is fed to the application. Harness: `eval/run_benchmark.py`
   (`--retrieval`, `--answers`, `--router`, `--holdout`) and `eval/baseline_retrieval.py`
   for the honest before number.

### Remaining before this brief can be called complete
- Finish, validate and activate the segment build, then re-measure; compare against the
  page-level numbers and the replayed old pipeline.
- Run the `--answers` pass and manually review the gender-equality response against the
  actual PDF pages 50 and 257, preserving the Inglehart and Norris attribution.
- Live cloud and Ollama fallback check, browser verification, app left on port 786.
- Record measured failures in Handsover.md. Do not claim universal coverage.

## Acceptance criteria still unmet — status as of 2026-11-12 00:36

Implementation is written for every numbered step above. Verification is almost entirely
outstanding, so this brief is NOT complete. The operational checklist with exact commands and
pass conditions is in Handsover.md under "Remaining verification checklist".

| Step | Implementation | Verified by real output |
|------|----------------|-------------------------|
| 1 Reproduce and trace | done | NO — no real trace captured; every file in data/diagnostics was mocked test output and has been archived |
| 2 Audit, child chunks, staged index | audit done over 689 pages, 181 flagged; chunking and staging written | NO — the staged build was interrupted and never activated, so the layer is inert |
| 3 Multilingual retrieval and fusion | done | IN PROGRESS — page-level baseline only, because step 2 is inactive |
| 4 Paragraph context and sectioned output | done | NO |
| 5 Full, partial and not-found coverage | done | NO |
| 6 Per-claim verification | done | NO |
| 7 Honest model and provider status | done, with regression tests | PARTLY — tests pass; no browser check |
| 8 Human-reviewed benchmark | 48 reviewed cases plus harness | NO — no results file yet |

What has actually been demonstrated: the offline suite at 122 passed, the frontend JavaScript
syntax check, the extraction audit, and real (not simulated) Gemini HTTP 429 falling back to
local qwen3:1.7b.

The brief's own completion requirements that remain unmet: real book queries against the
repaired pipeline; the manual inspection of the gender-equality answer against PDF pages 50
and 257 with the Inglehart and Norris attribution preserved; the browser check with saved
evidence; the app left running on port 786; and updates to Architecture.md, Desgin.md,
Memory.md, PRD.md, Rules.md, TASKS.md, VERIFICATION.md and RUN_COMMANDS.md.

Step 2 gates steps 3 to 6: any retrieval or answer number measured while the segment index is
inactive describes the OLD page-level pipeline and must be labelled as such. Do not present
it as the repaired result, and do not weaken verification to raise the answer rate.

---

## Status after the measured session of 2026-11-12 13:30

The table earlier in this file is superseded. Full detail, including every number and every
failure, is in Handsover.md under "Coverage repair — measured session, 2026-11-12".

| Step | Implementation | Verified by real output |
|------|----------------|-------------------------|
| 1 Reproduce and trace | done | **YES** — real traces in `data/diagnostics/`, e.g. `20261112-132957-explain-gender-equality-in-detail.json` (66 s, real request, real models). |
| 2 Audit, child chunks, staged index | done | **YES** — build `20261112-094445` active, 3338 segments / 661 pages, `validate ok: true`. A real chunker bug was caught by `validate` and fixed. |
| 3 Multilingual retrieval and fusion | done | **YES, measured** — reviewed page reaches the answering model 0.643 -> 0.810 over 42 answerable cases. |
| 4 Paragraph context and sectioned output | done | **YES** — whole parents sent once as numbered spans; evidence fitted to the answering model (6/1500 local measured better than 8/2400). |
| 5 Full, partial and not-found coverage | done | **PARTLY** — the not-found and related-material paths are verified live. A verified *partial* answer has not been produced on local hardware. |
| 6 Per-claim verification | done, and strengthened | **YES** — batched per-claim verdicts plus two new code-checkable guards (concept, attribution), each with a regression built from the real page text. |
| 7 Honest model and provider status | done | **YES** — `/settings/models` labels verified live; real Gemini 429 confirmed directly, never described as absence of book evidence. |
| 8 Human-reviewed benchmark | 48 cases plus harness | **RETRIEVAL ONLY** — the `--answers` pass was never run (4.5-7 hours). No answer-stage rate exists. |

### The brief's central question, answered honestly
`Explain Gender Equality in detail` now **retrieves correctly**: reviewed pages 50 and 257 are
evidence windows 1 and 2 in 2.6 s, and the whole request completes in 66 s instead of 866 s or
an HTTP 500. It does **not** yet produce the verified scoped answer this brief asked for.

The local model drafts 8 claims and all 8 are rejected: 2 from page 50 for presenting Inglehart
and Norris's quoted view without naming them, and 6 for resting on pages about *constitutional*
equality and women's protection rights rather than gender equality. An earlier intermediate
output did report `grounded: true` with those fabrications, and manual review against the PDF
caught it — which is exactly why the two code guards now exist. The reader is shown pages 50 and
257 as related material with working page links, and told plainly that the book does not directly
answer the question.

So: steps 1-4, 6 and 7 are done and demonstrated. The remaining gap is step 5's *partial* answer
and step 8's answer-stage measurement, and the cause is the answering model's capability on a
2 GB GPU, not retrieval, not grounding and not the book. Five separate defects that each produced
"no answer" were found and fixed along the way (claims past #8 discarded, expand replacing
evidence, expand crashing the request, the 180 s timeout killing every local answer call, and the
JSON grammar tripling generation time).

**Do not close this brief.** Two things remain:
1. Run `.\.venv\Scripts\python.exe -u -m eval.run_benchmark --answers --holdout --out eval/benchmark-answers.json`
   overnight. No answer-stage number exists until it finishes.
2. Produce the gender-equality answer on a model capable of writing an attributed,
   concept-correct claim. Gemini returns a real 429, so this could not be demonstrated.
   `tests/test_evidence_ranking.py` shows a correctly attributed claim on the real page-50 text
   passes both guards, so the pipeline is ready for it.

Do not weaken the concept or attribution guards to raise the answer rate, and do not tune
retrieval to rank the `seerah-*` table-of-contents pages higher — those benchmark expectations
are themselves wrong and need re-review.

## Status — 2026-11-16: explanation mode replaces claim lists as the default

The user's newest instruction supersedes the "fail closed on any unverified claim" reading of
this brief: answer every book question completely and respectfully, like ChatGPT/Gemini
explain, and never refuse when the book has the answer. What changed against each step:

- **Step 4 (coherent context, sectioned answers)** — done properly now: the model reads whole
  readable passages (12 windows / 12 000 tokens on cloud) and writes a sectioned Markdown
  explanation instead of ≤ 8 one-sentence claims. `app/agents/explain_agent.py`.
- **Step 5 (full / partial / none)** — hidden `<<full>>/<<partial>>/<<none>>` marker; partial
  answers state what the book does not cover; `<<none>>` triggers a second search first.
- **Step 6 (claim verification)** — replaced by a sentence-level audit over ALL sources that
  corrects or removes unsupported, contradicted, misattributed or overstated sentences, plus
  code-level citation validation. Attribution and hedging rules are in both prompts. The
  strict pipeline is still available (`answer_mode = 'strict'`) and still tested.
- **Step 7 (model visibility)** — the answering model is now the `explain` task, not the last
  trace entry; Gemini 503/429 falls back to `gemini_alternates` before another provider.
- **Step 8 (benchmark)** — `eval/explain_eval.py` measures the answer stage over all 48
  reviewed cases; results in Handsover.md and VERIFICATION.md.

Next step if interrupted: read the top section of Handsover.md.

- 2026-11-16 later: answers use direct teaching voice; "kaun si book / reference" returns the reviewed reference card. See Handsover.md.

- Loop 1: attribution of footnoted quotations restored (full writer names in source notes).

- Reference card affirms the source on request; answers 450-1100 words; Islamic UI redesign. See Handsover.md.

- Loop 2: one citation per page, script-mixing guard, list rendering fix.

- Second book "Creation of Man" indexed and answerable; multi-book citations and reference cards. See Handsover.md.

- Router no longer refuses unsure questions; heading windows include their paragraph; audit bounded to 25 s.

- Off-topic questions no longer show unrelated passages (programming rule; model-chosen related pages; not_in_library). Loop 3 benchmark cases for Creation of Man.
