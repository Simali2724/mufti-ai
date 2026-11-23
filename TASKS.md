# Tasks and checkpoint
Updated: 17 November 2026. **"Open now" is the consolidated, prioritised list — start there.**
Older checkpoints below are history; their unticked items were merged into "Open now".

## Open now (priority order)
- [ ] **After the quota reset (~13:30 IST):** ask one long question and confirm `audit_tier: strong` (2.5-flash or 3-flash-preview) with chunking in the trace; then run residual_audit with a judge that did not audit (e.g. gemini-3.5-flash) on ≥6 new and ≥6 old answers.
- [ ] **Accuracy measurement still owed (first attempt inconclusive, see VERIFICATION 01:15):** when Gemini is not overloaded, run `python -m eval.residual_audit --limit 4 --model gemini-3-flash-preview --out eval\residual-audit-after.json` and the same with `--skip 4 --limit 6 … before-3flash.json`; compare flag rates (baseline with 2.5-flash judge: 3/62 = 4.8%).
- [ ] Verify the chunked strong audit live on a 30+ sentence answer (not yet exercised: 2.5-flash was rate-limited during the check).
- [ ] Review drafts from reader feedback when 👎 entries exist: `python -m eval.feedback_to_cases` → check pages in the book → copy reviewed cases into `eval/book_benchmark.jsonl`.
- [ ] User: try the mic once with real speech (Urdu + Hinglish) and report any wrong transcription.
- [x] ~~Re-measure live latency with the new 60 s stream timeout~~ — done loop 4: no stall this time; real bottleneck was cold search (fixed) (`eval.probe "Misaq-e-Madina kya tha?" --mode gemini`); if `gemini-3.5-flash` keeps stalling, measure making `gemini-2.5-flash` primary.
- [ ] Full 60-case answer benchmark after a quota reset, server stopped: `.\.venv\Scripts\python.exe -u -m eval.explain_eval --mode gemini --out eval\explain-eval-gemini-v2.json --delay 8`
- [ ] Click through the chapter explorer, Focus chip, Download and Print in a real browser (headless screenshots + HTTP done).
- [ ] Ask the user to open `/hooks` once (or restart Claude Code) so the new Stop/PreCompact handover hooks load.
- [ ] Review page-hit misses (`state-en-2`, `comp-en-1`) and re-review the `seerah-*` expectations against prose (do not tune retrieval to them).
- [ ] OCR correction workflow for the 28 low-quality pages (`data/book-corrections/` is read by the code but does not exist yet).
- [ ] Decide with the user: move OLLAMA_MODELS permanently to C: (D: drive has been unstable).
- [ ] Recommend a paid Gemini (or Claude/OpenAI) key: free tier ≈ 20 requests/day/model.
- [ ] Feature backlog: see ADD_FEATURE.md "Feature ideas backlog" (quiz, bookmarks, compare books, glossary, feedback loop).

## Improvement loop — iteration 8 (2026-11-18): photo / file / drag & drop
- [x] `POST /extract` (local OCR/PDF/text) + `POST /find` (no-model page finder) + camera, upload, drag & drop, paste UI; tour/Guide step in 4 languages.
- [x] Measured: Nastaliq `urd_naw` reads 72/86 Urdu words vs 40/58 (`urd`) on scanned pages 257/51 → made default.
- [x] "Photo" of 4 real book pages (2 Urdu, 2 English) → `/find` puts the right page at rank 1 in 4/4; OCR 2.3-3.0 s per page.
- [x] Real Chrome: drop → OCR 0.47 s → Find → page 73 "Strong match"; Explain this → fully answered, fact-checked, 9 citations. 289 tests.
- [ ] Camera capture not tested (needs a physical camera + permission prompt). Handwritten text and phone photos at an angle not measured.

## Improvement loop — iteration 7 (2026-11-18): accuracy
- [x] Data: 84 traces — 76/957 draft sentences (8%) flagged by the audit; 119 sentences reached readers without a citation.
- [x] `eval/residual_audit.py`: baseline on 6 final answers with gemini-2.5-flash judge → 3/62 (4.8%) still flagged.
- [x] Two-tier audit (strong → lite), parallel chunks for long answers, citations for uncited sentences, number hints, quote check.
- [x] Live bugs found and fixed: Gemini HTTP 400 on the bounded schema; the strong audit's failure tripped the whole Gemini provider (next question went local, 216 s). Regression tests added.
- [x] Live after fixes: 3/3 answers audited (strong on 22 sentences in 30 s; 2 lite after strong timeouts before chunking); 4 citations added, 2 non-verbatim quotes un-quoted, 2 number flags.
- [x] 281 tests pass.

## Improvement loop — iteration 6 (2026-11-18): directions cover the new features + cache fix
- [x] Tour 7 → 9 steps (Topic index, Saved answers) and Guide 10 → 12 points (Quiz, 👍/👎, Topic index, Saved) in English, Hinglish, Urdu, Hindi.
- [x] Real-Chrome check exposed a stale cached tour.js → frontend files now sent with `Cache-Control: no-cache`; test added (272 passed).

## Improvement loop — iteration 5 (2026-11-18): Topic index
- [x] `GET /topics` (reviewed concepts + 361 outline entries) and ▦ Topic index view with search, Explain/Summary/Focus.
- [x] Real-Chrome check found English queries returned 0 Urdu sections → added cross-script matching through concept forms ("equality" 0 → 2, "madina" 0 → 4, "constitution" 6).
- [x] 271 tests (+1). No model call.
- [ ] Concept lexicon has only 10 concepts — extending it is a reviewed content change (Rules.md 18), not an automatic one.

## Improvement loop — iteration 4 (2026-11-18): first-question speed
- [x] Live trace: 65 s total, of which **retrieve 42.5 s** (cold), explain 16.5 s, audit 2.7 s.
- [x] Profiled cold vs warm: bge-m3 load 10-19 s, first Chroma query 7.6 s, first search 7.2 s → warm search 0.33 s.
- [x] Background warm-up at start (6.3 s, server reachable immediately) + 30 min embedding keep-alive in cloud mode.
- [x] After: same question → **retrieve 3.25 s**, total 41.4 s (explain 30 s = Gemini variance). 270 tests.
- [ ] If Gemini answer time stays 15-30 s, consider gemini-2.5-flash first (measure several runs before changing).

## Improvement loop — iteration 3 (2026-11-17): Quiz me
- [x] `POST /quiz` builds MCQs only from cited sentences of a grounded answer in server-side history; code drops unsupported questions.
- [x] Offline test caught an invented-date question passing on the word "was" → check tightened (content words of the correct option, no new numbers). 266 tests pass.
- [x] Live: Hinglish Misaq answer → 4.6 s, 3 of 4 questions kept, each with page citations; real-Chrome quiz UI verified.

## Improvement loop — iteration 2 (2026-11-17): saved answers
- [x] ☆ Save / ★ Saved answers view (search, open with citations, download, two-step delete); local atomic JSON store.
- [x] 3 tests (`tests/test_saved.py`); suite 261 passed; real-Chrome save → list → search → open → delete verified; test data removed.

## Improvement loop — iteration 1 (2026-11-17): answer feedback
- [x] 👍/👎 with reasons + note on every answer; local JSONL; `/feedback`, `/feedback/summary`; rate-limited.
- [x] `eval/feedback_to_cases.py` → unreviewed draft cases (no expected pages until a human checks the book).
- [x] 4 tests (`tests/test_feedback.py`); suite 258 passed; real-Chrome 👎 flow verified (test entry removed).

## Checkpoint — 17 November 2026 (2): voice, English UI, welcome popup, arrow tour
- [x] Mic: one recording at a time; Stop / Cancel / Esc; accidental-tap guard; 60 s limit; never auto-sends.
- [x] `POST /transcribe` (text only) + Whisper language hint; 4 tests.
- [x] UI text English by default; welcome popup with directions language; 🌐 header button.
- [x] 7-step arrow tour + Guide translated into English / Hinglish / Urdu / Hindi.
- [x] Verified in real Chrome (stubbed mic); 254 offline tests pass.
- [ ] One real spoken test by the user (Urdu and Hinglish) through local Whisper.

## Checkpoint — 17 November 2026 (agent & GenAI upgrade)
- [x] Answer styles: detailed / short / simple / study notes (UI + API + voice), grounding unchanged.
- [x] Follow-up questions in the same model call (`<<next:>>`), outline fallback for local models.
- [x] Topic suggestions for vague questions and empty-library answers.
- [x] Chapter focus (scope) in retrieval with honest whole-library fallback.
- [x] Chapter explorer UI (Explain / Summary / Focus) + `GET /books/{id}/outline`.
- [x] Starter topics (`GET /suggestions`), Guide dialog (how-to, setup check, shortcuts), keyboard shortcuts.
- [x] Download .md / Print for every answer; "Same question" re-ask in another style.
- [x] Setup check: `.\doctor.ps1`, `GET /health/setup` (English + Hinglish fixes, no secrets).
- [x] Stalled cloud streams switch model after 60 s (was 180 s) — offline-tested, live re-measure open.
- [x] Auto handover snapshot (`tools/handover_snapshot.py`) + Claude Code Stop/PreCompact hooks.
- [x] Docs: AGENTS.md, CLAUDE.md, USER_GUIDE.md, ADD_FEATURE.md, FEATURES.md; REPAIR_PROMPT.md prompt + triage; Architecture "At a glance".
- [x] 250 offline tests pass (+19); UI markdown test covers marker stripping; live HTTP checks recorded in Handsover.md.

## Completed implementation
- [x] Local PDF ingestion, OCR, hybrid search and evidence-verification pipeline.
- [x] Attractive multilingual UI and local Whisper voice path.
- [x] Cloud providers, configurable model IDs/priorities and Ollama/Gemma fallback.
- [x] Persistent selected-model strip beside the composer.
- [x] Request-scoped live task/provider/model status events.
- [x] Saved model execution and citation metadata for new history turns.
- [x] Distinct no-evidence/verification/service-failure diagnostics.
- [x] Mahomet/Mohammed alias expansion and wider pre-reranking candidate pool.
- [x] One extra evidence batch when the first three candidates contain no direct answer.
- [x] Architecture.md, Desgin.md, Memory.md, PRD.md, Rules.md, TASKS.md, Handsover.md.

## Validation checkpoint
- [x] 81 offline checks passed; JavaScript syntax passed.
- [x] Live screenshot question: cited pages 201/234; known piety question: cited page 51. Both grounded=true.
- [x] Browser verified selected model, actual Gemini/Ollama step names, fallback badge and retained citations/history after reload.

## Next quality work
- [ ] Create a manually verified 20+ question multilingual book benchmark with expected pages and supporting quotes.
- [ ] Measure retrieval recall and verified-answer coverage against that benchmark.
- [ ] Review/correct OCR for low-quality pages and establish a correction/reindex workflow.
- [ ] Compare local Qwen/Gemma and user-configured cloud models on the same benchmark.
- [x] Real Gemini generation succeeded; observed connection failure continued to local Ollama. Actual Gemini 429 was also observed; Ollama verification completed in the browser test.
- [ ] Consider more evidence per question only after measuring context-window and latency tradeoffs.
- [ ] Public hosting/authentication remains outside current scope.

## Author/OCR follow-up
- [x] Inspect title/publication scans and identify corrupted author OCR.
- [x] Add reviewed PDF-hash-bound author, publisher, title, ISBN and first-publication facts.
- [x] Verify six real API cases in English/Urdu/Hindi with page citations, approximately 0.5–0.9 seconds each.
- [x] Test wrong-book rejection, changed-PDF invalidation, saved history, and no model generation on this path.
- [x] Correct Auto English detection for questions containing Urdu book-title terms.
- [ ] Broader substantive book-question coverage needs a manually checked benchmark and targeted OCR corrections. Metadata success does not establish universal answer accuracy.


## Runtime repair follow-up
- [x] Restore and checksum-verify required models in configured D: model store.
- [x] Remove missing-default-model search blocker.
- [x] Distinguish service failures from lack of book evidence.
- [x] Preserve hybrid ranking and prioritize exact content words in quotes.
- [x] Validate 109 tests and record live fallback result.
- [ ] Build a manually annotated multilingual body-text benchmark and improve measured weak areas.
- [ ] Reduce multi-minute local fallback latency.

## Coverage repair checkpoint — 2026-11-12
Measured results and the exact outstanding work are in Handsover.md under
"Coverage repair — measured session, 2026-11-12". Ticked items below were observed, not assumed.

### Done and measured
- [x] Rebuild, validate and activate the child-segment index. Active: `20261112-094445`,
      3338 segments / 661 pages / `bge-m3`, `validate` ok with no issues.
- [x] Fix the chunker bug `validate` caught: a short trailing remainder was folded into the
      previous child together with its overlap, duplicating text. Now 0 of 3338 offenders.
- [x] Honest retrieval before/after over all 48 cases: reviewed page reaches the answering
      model **0.643 -> 0.810**; candidate recall 0.810 -> 0.881; misses 15 -> 8.
- [x] The exact failing question retrieves pages 50 and 257 as evidence windows 1 and 2 in
      about 2.6 s.
- [x] Add the content-word query variant; it fixed state-en-1/2/3 and held-out cm-en-7.
- [x] Measure the model query-rewrite and remove it for local models: identical recall,
      total retrieval time 1102 s -> 106 s.
- [x] Fix claims past #8 being silently discarded by the verifier schema's claim-id range.
- [x] Fix the expand round replacing, rather than extending, the first round's evidence.
- [x] Fix the expand round crashing the request with a duplicate `queries` keyword.
- [x] Give local providers their own timeout; a legitimate multi-minute local answer call was
      being killed at 180 s and reported as "no answering model could be reached".
- [x] Strip length/count bounds from the local JSON grammar: identical output, 394 s -> 215 s.
      Bounds now enforced in code.
- [x] Stop sending each passage to the answer model twice.
- [x] Cache the BM25 index instead of rebuilding it per query variant.
- [x] Size evidence to the answering model: 6 windows / 1500 tokens locally measured faster
      AND produced more resolvable claims than 8 / 2400.
- [x] Add the concept guard and the attribution guard to code-checkable verification.
- [x] Stop discarding a supported claim for a missing full stop.
- [x] Local requests take one search round; two pushed a live request past 1800 s.
- [x] 133 offline checks pass; `node --check frontend/app.js` passes.
- [x] App serving http://localhost:786; `/health`, `/settings/models` and a live `/chat`
      request verified over HTTP.
- [x] Manually review the gender-equality answer against PDF pages 50 and 257. **It failed
      review** — see the next section. This is recorded as a failure, not a success.

### Open — the honest remaining work, highest value first
- [ ] **Run the `--answers` benchmark pass.** Not run: 4.5-7 hours at 340-550 s per case. There
      is therefore no measured `answered_rate`, `false_refusal_rate`,
      `answered_absent_topic_rate` or `citation_page_accuracy`. Do not quote such a number.
      `.\.venv\Scripts\python.exe -u -m eval.run_benchmark --answers --holdout --out eval/benchmark-answers.json`
- [ ] **Answer quality on local models is the blocker, not retrieval.** qwen3:1.7b returned
      `grounded: true` on the gender-equality question with three fabricated claims drawn from a
      page about constitutional equality, and dropped the Inglehart/Norris attribution. The new
      guards reject that output, so the app now refuses honestly instead of fabricating. Getting
      a real answer needs a more capable model; Gemini is quota-exhausted (real HTTP 429).
- [ ] Measure the false-refusal cost of the concept and attribution guards across the benchmark.
      The attribution guard is deliberately conservative and may over-reject.
- [ ] Browser check of the provider strip and a live answer, with a saved screenshot. Not done
      this session.
- [ ] Re-review the `seerah-en-1/ur-1/hg-1` expected pages: 14, 17, 26 and 28 are
      table-of-contents pages with no supporting prose. The benchmark expectation is wrong, not
      the retrieval. Do not tune retrieval to satisfy them.
- [ ] Explain the `cm-hi-1` and `cm-en-6` retrieval misses.
- [ ] OCR correction workflow for the 181 flagged pages (`data/index/extraction-audit.json`);
      `data/book-corrections/` does not exist yet, though the code reads it.
- [ ] Reduce local latency further. At 1.6-3.0 tok/s a sectioned answer is inherently minutes.

## Checkpoint — 13 November 2026 (answer-stage repair)

### Done this session
- [x] Audited the live state before changing anything: segment build `20261112-094445` active
      (3,338 segments / 661 pages), 133 tests passing, retrieval reproducing pages 50 and 257.
- [x] Reproduced the gender-equality failure and traced it to the drafting and verification
      stages, not to retrieval.
- [x] **Targeted per-claim repair** (`app/agents/repair_agent.py`) wired into the graph between
      `verify` and `expand`. Deterministic attribution repair costs no model call.
- [x] Attribution guard scoped to the quoted span instead of the whole window.
- [x] Concept guard scoped: span, then rival-concept veto, then parent paragraph.
- [x] Relevance verdict gates only questions that demand a relation; self-contradicting
      verdicts no longer manufacture refusals.
- [x] New code-checkable guards: grounding floor, copied span, dropped qualification, one
      sentence per claim, bibliography-only span.
- [x] `explanation_unverified` and `insufficient_evidence_after_search` separated from
      "the book does not contain this", in the API, the formatter and the UI.
- [x] Book / Chapter / Section / page-range tree from the PDF outline
      (`app/ingestion/book_tree.py`): 9 chapters, 301 sections, 0 validation problems.
- [x] Clean outline titles replace the OCR-noise `chapter` field on evidence and citations.
- [x] Bounded tree navigation route (`app/retrieval/tree_nav.py`), measured and defaulted off.
- [x] PageIndex evaluated against the real package and documented as not adopted, with reasons.
- [x] `off_concept_factor` swept against the benchmark; 0.9 shipped at no retrieval cost.
- [x] Benchmark harness: resumable `--answers`, `--windows`, `--mode` provider override, and
      concept-aware selection so it measures what the app actually does.
- [x] 25 new failure-driven tests in `tests/test_answer_quality.py`, each written from a
      measured failure and testing its guard in both directions. Suite: 158 passing.
- [x] Live verification over HTTP against the running server, and all citation/PDF endpoints.
- [x] Full working backup at `C:\mufti-ai-salvage` taken during the D: drive outage.

### Next
- [ ] Finish the local-model `--answers` pass for a like-for-like comparison against the cloud
      numbers. Use `--resume`; it is several hours on this GPU.
- [ ] Re-review the three `seerah-*` benchmark expectations. They point at contents and
      heading pages (page 17's entire English layer is `i ii iii iv v i ii iii`), so their
      recall contribution is not meaningful until the expected pages are corrected against the
      book's actual prose. Do not tune retrieval to satisfy them.
- [ ] `cm-hi-1` and `cm-en-6` retrieval misses are still unexplained.
- [ ] Review OCR for the 28 low-quality pages and establish a correction/reindex workflow.
      The outline tree now gives a reliable place to start: it says what each page should be
      about.
- [ ] Consider using outline titles as an additional embedded field at index build time, which
      would put correctly spelled Urdu into the vector index rather than only into ranking.
- [ ] Browser check with the Chrome extension was not possible this session; the UI was
      verified over HTTP instead (see VERIFICATION.md).

## Checkpoint — 16 November 2026 (explanation mode, user request: no false refusals, ChatGPT-style answers)

### Done and verified
- [x] New default answer path `app/agents/explain_agent.py`: streamed, sectioned, cited
      Markdown explanation + sentence-level audit; strict pipeline kept (`answer_mode`).
- [x] Streaming end to end (Gemini/Ollama/OpenAI/Anthropic → SSE `draft` → live UI draft).
- [x] Gemini routing: per-model alternates, per-task lite models, daily-quota cooldown,
      timeout → next model, audit never on the local model.
- [x] Reviewed book title/author in answers instead of the PDF file name.
- [x] OCR legibility judged per line/script for model input (fixed `comp-en-4`).
- [x] `<<none>>` for absent topics instead of "the book does not discuss X" answers.
- [x] UI: Markdown, `[n]` chips → page dialog, drafting cursor, verification badge, copy.
- [x] Saved preference switched to Gemini-first (`gemini-3.5-flash`) with Ollama fallback.
- [x] `eval/explain_eval.py`; full live run 41/42 answered, page-hit 0.854; targeted rerun
      after fixes: 6/6 answered, 0/4 absent answered.
- [x] 205 offline tests pass; live HTTP streaming, follow-up and history verified.

### Next
- [ ] Full 48-case rerun after the daily quota reset (`eval\explain-eval-gemini-v2.json`).
- [ ] Review page-hit misses (`state-en-2`, `comp-en-1`, `seerah-*` expectations).
- [ ] Script-mixing guard for Hindi answers from lite models.
- [ ] Merge duplicate-page citations.
- [ ] Browser check when the Chrome extension is connected.
- [ ] Recommend a paid Gemini (or other) key to the user: free tier = 20 requests/day/model.

- [x] Direct-voice detailed answers; "which book / reference?" card (217 tests).
- [ ] Hinglish piety question misses page 51 (retrieval).

- [x] Loop 1: quoted-writer names preserved and attributed (page 51); 220 tests.
- [x] ~~Hinglish piety question misses page 51~~ — false lead (page not about the Prophet's own worship).

- [x] Reference card says "Ji haan, is kitab se" + previous question's pages; coverage full.
- [x] Detailed answers (450-1100 words) — live 583 words, audited.
- [x] Islamic UI redesign (emerald/gold, ﷽ arch hero, answer cards, dark mode); screenshots in eval/ui-*.png.

- [x] Loop 2: same-page citations merged; Hindi/Urdu script guard; numbered-list rendering; 223 tests + tests/ui_markdown.test.js.
- [ ] Full 48-case rerun after quota reset (~13:30).

- [x] Second book "Creation of Man" indexed (98 chunks), segment build 20261116-121031 active, reviewed metadata + outline, multi-book answers/cards/UI; 224 tests.
- [ ] Decide with the user: move OLLAMA_MODELS permanently to C: (D: drive unstable).
- [ ] Full 48-case rerun now that two books share retrieval (book-1 cases may pick up book-2 passages).
- [x] Add benchmark cases for Creation of Man — loop 3: 12 reviewed `com-*` cases (4 languages, 3 holdout, 1 absent: cloning); every case carries `book`; explain_eval scores (book, page).
- [ ] Run the 60-case eval after the ~13:30 quota reset (stop the server first).

- [x] "Tissues and Body Form" false refusal fixed: no model router (search every question), heading windows bring their paragraph, short English lines kept, audit time-bounded; 228 tests.

- [x] Off-topic questions: programming rule, model-chosen related passages (<<none: n>>), not_in_library outcome; 231 tests.
