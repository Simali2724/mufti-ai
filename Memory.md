# Project memory
Last updated: 11 November 2026, Asia/Kolkata.

## User intent
Build an attractive Mufti AI app under D:\, host locally on requested 0786 (numeric port 786), answer strictly from the uploaded book, support Ollama plus Anthropic/OpenAI/Gemini with cloud-first fallback. Gemma is an Ollama model, distinct from Gemini cloud. Show whichever model the user selects and the actual model running. Provide durable documentation so another AI can resume without chat history.

## Installation facts
- Project: D:\mufti-ai. Python environment: .venv\Scripts\python.exe.
- Original PDF: D:\Muqaddima-Seerat-ur-Rasool-1_1.pdf; working copy under data/books.
- Catalog: 689 PDF pages, 662 passages, 28 unreadable/review pages. OCR remains imperfect on other pages too.
- Available local models last checked: qwen3:1.7b, qwen3:4b, gemma3:1b, llama3.2:3b; embeddings bge-m3 and nomic-embed-text. Default answering choice was qwen3:1.7b. Read model-settings.json for current user selection.
- Machine has a small 2 GB GPU. Generation can take minutes; serialize model switching.
- Initially cloud keys were absent. On this improvement run the user had configured Gemini and selected Gemini preferred; live Gemini generation succeeded. Do not print .env or assume subscriptions imply API quota.
- D: disconnected once and the user reconnected it. If absent, check drive availability before treating it as source loss.

## Decisions to preserve
Strict book grounding, exact quote verification, physical PDF page citations, fail-closed unsupported drafts, same-session locking, request-scoped model preferences, cloud-first/local-last fallback, and ScopedSqliteSaver's short-lived connections. Keep voice local by default. Use literal Windows paths and hidden background launches. Never overwrite live data with workspace staging copies.

## Current improvement
User screenshot showed generic refusals and an unhelpful Ollama connected label. Added visible selected model, live model/task status, saved execution/citation metadata and distinct refusal reasons. Expanded name aliases and retained more candidates before reranking; no-answer generation can inspect a second evidence batch. Explicit Urdu language selection explains the screenshot's Urdu refusal. This does not prove that all questions can be answered.

## Maintenance
Update TASKS.md and Handsover.md after each verified milestone, recording exact checks, active blockers, changed files and next action. Never store secrets or private conversation content in handover documents.

Final improvement validation: 81 checks passed; real Gemini 429 fallback to Ollama observed; screenshot question answered with pages 201/234 and piety question with page 51. History reload keeps citations and model execution. Full-book coverage and OCR correction remain next tasks. See Handsover.md for exact timings.

## Author failure correction
The author question failed because OCR corrupted the author name on title/publication pages 2/3. Visual inspection of the original PDF confirms Dr. Muhammad Tahir-ul-Qadri. The app now answers narrow bibliographic questions directly from reviewed, hash-bound page facts. The user-requested author wording was tested in the real UI. An English question containing Seerat/kitab now remains English in Auto mode when English grammar is present without Hinglish question grammar. Broad body-text quality still requires systematic evaluation and OCR review.


## Runtime repair checkpoint — 2026-11-11T23:10
- Exact author question now returns English in Auto mode: Dr. Muhammad Tahir-ul-Qadri, PDF page 3, grounded=true, about 1.2 seconds. This is a visually reviewed publication fact, not a generated answer. Evidence: eval/author-auto-final.json and author-verification.jpg.
- Ollama had stopped, and OLLAMA_MODELS points to D:/ollama-models whereas required models remained in the old C: store. Copied bge-m3:latest, qwen3:1.7b and gemma3:1b into D:/ollama-models with every referenced blob SHA-256 verified. Originals and existing llama3.2:3b were preserved; no environment settings changed.
- Fixed app/core/resources.py: first model selection no longer guesses and unloads an uninstalled default. An already-removed model returning 404 does not block switching; other service errors still propagate. Regression tests cover the actual reproduced failure.
- app/agents/formatter.py now reports unavailable search/answer services in the requested language instead of falsely saying the book has no evidence. New tests/test_model_resources.py and updated HTTP test fixture in test_fallback.py. Backups: backups/model-switch-20261111.
- Final full suite: 109 passed. Frontend JavaScript syntax passed.
- A live run initially returned an unsupported page-235 answer despite grounded=true. Preserve eval/rejected-book-quality-example.json as a manually rejected result, never a success metric. The reranker was discarding hybrid ranking and quote selection was overweighting common words in a noisy translation. Fixed reranker.py to preserve hybrid order when no cross-encoder runs, and answer_agent.py to prioritize original content words over translation stopwords. Strengthened verifier attribution instructions. Backups: backups/evidence-ranking-20261111; regressions: tests/test_evidence_ranking.py.
- Live content question: What does the book say about personal piety and worship of God?
  grounded=True; provider=ollama; model=qwen3:1.7b; pages=[51]; retrieved_count=18; latency=84.2s; reason=.
  Full output: eval/restored-book-live.json. Real Gemini 429 responses triggered local Qwen fallback during this run.
- App is served at http://localhost:786 and Ollama at 127.0.0.1:11434. Current processes were started in retained tool sessions, so check listeners when resuming; do not assume they survive desktop/app exit. Do not trust recorded PIDs.
- Selected answering provider remains Gemini / gemini-2.5-flash; fallback remains Ollama / qwen3:1.7b. Local installed answer models include Qwen, Gemma and Llama. Never print .env.
- Remaining work: broad, manually checked multilingual book benchmark; OCR repair for failed passages; reduce local fallback latency. This checkpoint does not establish that every book-content question is answered correctly.
- First resume steps: read this latest checkpoint, run the commands in RUN_COMMANDS.md, check /health and /settings/models, then inspect the saved live result and TASKS.md. Do not rebuild or overwrite the index or histories.

Manual quality review of the final rerun: the returned page-51 statements match the English text in the indexed passage and directly address the question. Qwen generated and verified this answer after actual Gemini 429 responses; latency was 84.172 seconds. The previous page-235 output is a failed quality example even though its automated grounded flag was true. Automated grounding is not a substitute for a human-reviewed evaluation set.
## Coverage repair session — 2026-11-12

### Hardware, now measured rather than assumed
NVIDIA GeForce MX450, **2 GB** VRAM (plus Intel Iris Xe), confirmed from
`Win32_VideoController`. qwen3:1.7b sits fully in VRAM (1.44 GB) and still generates at
**1.6-3.0 tokens/s**. Everything about the local pipeline follows from that number: a sectioned
answer is 600-900 output tokens, so one answer call is 215-580 s and a full request is minutes.
Design to reduce *output tokens* and *number of model calls*, not context size — dropping
`num_ctx` from 8192 to 4096 changed nothing.

### Decisions taken on measurement, with the numbers that justify them
- **Child-segment index is live.** Build `20261112-094445`, 3338 segments / 661 pages / `bge-m3`.
  Before this session it had never been activated, so every earlier retrieval measurement
  described the old page-level pipeline.
- **Content-word query variant.** A long question dilutes BM25. `sanitation` alone ranks the
  right page first; the same word inside a 12-word question does not place it in the top 30.
- **No model query-rewrite on local models.** Identical recall, 1102 s -> 106 s over 29 cases.
  The local 3B model's translations were corrupt (Devanagari inside Urdu, Cyrillic characters).
- **Strip length/count bounds from the local JSON grammar.** llama.cpp expands `maxLength` into
  GBNF repetition: identical output, 394 s -> 215 s. Bounds enforced in code instead. Removing
  the schema entirely gives 0 usable claims, so keep the structure.
- **Per-provider timeouts.** 180 s cloud, 900 s local. A single 180 s timeout was killing every
  local answer call and the reader was told no answering model could be reached.
- **One search round locally.** The second answer call was observed timing out twice, taking a
  request past 1800 s until the client gave up. With one round the same live question through
  the server completed in **66 s**.
- **6 windows / 1500 tokens locally.** Measured faster than 8 / 2400 *and* produced more
  resolvable claims.
- **`model-settings.json` changed from `llama3.2:3b` to `qwen3:1.7b`.** llama3.2:3b is 2.02 GB
  against a 2 GB GPU and produced only claims that verification rejected. Reversible in the UI.

### The thing to remember about answer quality
Retrieval is fixed and measured; **answer generation on this hardware is not, and that is a
model-capability limit.** The gender-equality question was manually reviewed against PDF pages
50 and 257 and the output **failed**: qwen3:1.7b returned `grounded: true` while drawing three
claims from page 280, which is about *constitutional* equality among the Charter of Madinah's
parties, and asserting things about the Quran and about "both genders" that the span never says.
It also dropped the Inglehart/Norris attribution, turning their quoted view into the book's own
conclusion. A 1.7B verifier approved a 1.7B drafter's fabrications — the same failure class as
`eval/rejected-book-quality-example.json`.

Two code-checkable guards were added in response, and verification got stricter, not weaker: a
**concept guard** (the span must carry a reviewed surface form of the concept the question
matched, so gender equality is not answered from constitutional equality) and an **attribution
guard** (a window crediting an outside writer in the book's "Surname, Title, p. N" form requires
any claim from it to name that writer). The question now returns `unsupported_claims` with pages
50, 257 and 282 shown as related material to read. That refusal is correct. It is still not an
answer, and the honest reason is the local model, not the book and not retrieval.

Never report a measured refusal as success, and never relax the guards to raise the answer rate.

### Operational lessons
- Only `GOOGLE_API_KEY` is configured, and it returns a **real HTTP 429** on every call —
  verified directly. Local-only is the actual operating mode. Never print `.env`.
- A long-running command started from the Bash tool is killed when its background shell is
  reaped; two benchmark runs were lost that way at 29/48 and 6/48. Use PowerShell
  `Start-Process ... -RedirectStandardOutput` for anything over a few minutes.
- D: reported "The device is not ready" once and recovered on its own. Check the drive before
  concluding data is lost.
- The uvicorn launch pid is not the listener pid. Find the listener; never trust a recorded pid.
- Three of the eight remaining retrieval "misses" are bibliographic questions answered by
  `bibliography.py` before retrieval runs, so they are harness artefacts, not product failures.
- Three more (`seerah-*`) expect table-of-contents pages that carry topic words but no prose.
  That is a benchmark ground-truth error to re-review, not a retrieval target.

## Answer-quality session — 2026-11-13

### The previous conclusion was wrong, and that is the thing to remember

The 2026-11-12 checkpoint said the pipeline was "demonstrably correct end to end" and that the
gap was purely "the local model's ability to write an attributed, concept-correct claim". It
was not. Three defects in the drafting and verification stages were manufacturing refusals no
model could have avoided:

1. There was **no targeted claim repair at all**. The brief asks for a rejected claim to be
   repaired from its own evidence before being abandoned; the only recovery route was a full
   re-search and redraft. The claim that failed on page 50 needed two words, not a new search.
2. The **attribution guard was window-wide**, so every sentence of a paragraph containing a
   footnote had to credit the footnote's author.
3. The **verifier contradicted itself**: it returned `answers_question=false` while its own
   feedback for the same claim read "The claim is fully entailed by the span."

When a model keeps failing a task, check what the surrounding code is doing to its output
before concluding the model cannot do it.

### Measured, 2026-11-13

- Gemini quota **has reset** and answers live. The previous session's "real HTTP 429 on every
  call" was a quota window, not a permanent state. Re-check before assuming a provider is dead.
- Retrieval, all 48 cases (42 answerable), shipping config: candidate_recall **0.881**,
  window_recall **0.810**, top3_recall **0.738**, median 2.4 s/question. Identical to the
  previous session's best, so the answer-stage work cost nothing in retrieval.
- Earlier numbers in this repo were taken at **8 evidence windows**; the shipping default is 6.
  Compare like for like with `--windows 8` or the comparison is meaningless.
- `off_concept_factor` swept against the benchmark: 0.55 gave window_recall 0.786, 0.75 gave
  0.810, **0.9 gave 0.810 with top3 0.738** (equal to no demotion at all). 0.9 shipped.
- Page-tree route: window_recall and top3_recall **identical**, candidate_recall 0.881 to
  0.857, ~0.1 s slower. No measured benefit, so it is off by default. The tree's *metadata* is
  used regardless and is genuinely valuable.
- Attribution-guard scoping releases 4.1% of spans across the 124 parent paragraphs that cite
  an outside writer, and page 50 remains fully covered.

### Decisions to preserve

- **The PDF outline is the only correctly spelled Urdu in this corpus.** 310 entries, clean
  text, physical page targets, versus OCR'd body text from legacy InPage fonts. Page 280's
  body reads "آینی مساوات کا جق"; its outline title reads "آئینی مساوات کا حق". Any future work
  on Urdu matching should start from the outline, not the body text.
- **Absence from the reviewed lexicon is not evidence that a passage is off topic.** Demoting
  everything the lexicon did not recognise cost a benchmark case (`west-en-2`). Only a passage
  carrying a *rival* reviewed concept is a distractor.
- **A guard must never shrink the evidence set.** The adjacent-concept cap is soft: it stops
  rival material crowding out better evidence, it does not leave the model with less than was
  available. A hard cap turned eight windows into three and lost the case.
- **Do not loosen the verifier prompt to raise the answer rate.** Telling the verifier "if the
  span states it, the claim is supported" immediately produced an approved fabrication:
  "Gender equality is a fundamental principle in Islam, emphasizing the equal rights and
  responsibilities of men and women" from a span that calls it a point of *difference* between
  Islam and the West. The prompt now carries that exact case as a worked negative example, and
  a code-level grounding floor catches it without relying on the model's judgement.
- **A small model will satisfy per-property guards by concatenation.** Asked to repair that
  fabrication, it kept the fabricated sentence and glued a correct attributed one onto the
  end; names present, hedge present, wording shared. Claims are now enforced to one sentence
  in code.

### The hardware fact that cost the most time

D: is an external SSD ("EVMNV/25 6GB") that disconnected repeatedly. At worst, 6,653 Windows
disk I/O errors in twenty minutes, the source PDF and every `.md` unreadable, and the server
killed mid-request by `OSError: [Errno 22] Invalid argument: '.env'`. `Get-ChildItem` happily
lists files whose contents cannot be read, so a directory listing proves nothing. Check the
drive before debugging the application. A complete working backup is at `C:\mufti-ai-salvage`
and the suite passes from it unchanged.

Ollama also wedged once after hours of heavy 2 GB-GPU work: a request hung with the server
idle and no model loaded. Restarting `ollama serve` cleared it. Suspect this when a request
hangs while the server process is using almost no CPU.

## Do not run the server and a benchmark against Ollama at the same time

Measured twice on 2026-11-13, and it cost roughly an hour before it was understood.

**Symptom.** A request hangs indefinitely. The application server sits at near-zero CPU, so it
looks like a deadlock in the graph. It is not. Ollama's HTTP API stays alive and answers
`/api/ps` and `/api/tags` normally, while **inference** never returns: a trivial five-token
`/api/chat` request times out with no response at all.

**Check it in one command.** If this does not come back in a few seconds, Ollama is wedged and
nothing in this repository is at fault:

```powershell
curl.exe -s --max-time 30 -X POST http://127.0.0.1:11434/api/chat -H "Content-Type: application/json" --data-binary '{\"model\":\"qwen3:1.7b\",\"messages\":[{\"role\":\"user\",\"content\":\"Say OK\"}],\"stream\":false,\"think\":false,\"options\":{\"num_predict\":5}}'
```

**Fix.** Restart Ollama. Recovery is immediate (about 15 s including the model load):

```powershell
Get-Process ollama* | Stop-Process -Force
Start-Process ollama -ArgumentList serve -WindowStyle Hidden
```

**Cause, and the rule that follows.** Both occurrences happened while the uvicorn server and a
separate evaluation process were driving Ollama at the same time. `app/core/resources.py`
holds `ollama_lock` to stop embedding and generation competing for this 2 GB GPU, but that
lock is **per process**: it cannot serialise a benchmark run against the live server. Two
processes alternately selecting `bge-m3` and `qwen3:1.7b` make Ollama load and unload models
against 2 GB of VRAM until it stops responding.

So on this machine, run **one** of them at a time. Stop the server before starting an
evaluation pass, or run the evaluation against the HTTP API instead of in its own process. A
machine with more VRAM would likely not show this, which is exactly why it must be written
down rather than rediscovered.

## Explanation-mode session — 2026-11-16

- **The user's requirement changed the trade-off.** They want every book question answered and
  explained like ChatGPT/Gemini, respectfully, and no refusal when the book has the answer.
  Default is now `answer_mode: explain`; grounding is kept by citations validated in code plus
  a sentence-level audit that corrects/removes bad sentences instead of refusing the answer.
- **Measured:** 48-case live run 41/42 answerable answered (0.976), page-hit 0.854, median
  23.5 s; after three fixes a targeted rerun answered 6/6 and declined 4/4 absent cases.
  A full post-fix run is still owed (quota).
- **Gemini free tier = 20 requests/day PER MODEL** (quotaId
  `GenerateRequestsPerDayPerProjectPerModel-FreeTier`). Earlier "Gemini always 429" notes were
  this daily per-model limit. Spreading across models is what makes the free key usable.
  `gemini-flash-latest` timed out on every call — removed from alternates.
- **A weak model must never judge a strong one.** The local 1.7B auditor replaced correct
  sentences with "This is supported by sources 2, 4, 7, and 12." Audit is cloud-only.
- **Legibility must be judged per line.** `spans_for` merges short lines, so one Urdu
  reference line made a clean English sentence look like broken Urdu (page 375, Duguit).
- **Initials split sentences** ("Philip K. Hitti"); `ABBREVIATION` protects them.
- Ollama is still required in cloud mode (bge-m3 embeddings). Never run `eval.explain_eval`
  and the server against Ollama at the same time.

- Loop 1 (2026-11-16): judging legibility per sentence split author initials and dropped quoted writers' names; judge the whole line first. Check whether an expected page actually answers the question before calling its absence a retrieval miss.

- UI can be checked without the Chrome extension: headless Chrome screenshot of `http://127.0.0.1:786/?session=<id>&theme=light` (see eval/ui-*.png).

- curl on Windows (Git Bash) mangles Hindi/Urdu text passed as a command-line argument — the app then sees '?' and answers needs_topic. Send JSON from a UTF-8 file with --data-binary @file.

- 2026-11-16: D: storm again (Event 153 retries, Errno 22). Ollama reading models from D: fails first ('PrefetchVirtualMemory failed', 'model not found'). The C: store %USERPROFILE%\.ollama\models has identical bge-m3/qwen3:1.7b; start Ollama with $env:OLLAMA_MODELS set to it. The Get-WinEvent StartTime filter returned misleading counts — group events by TimeCreated instead.
- Two books now: reviewed metadata per book (title, author, outline). A PDF outline can be junk; use a reviewed outline in data/book-metadata.

- Never let a model classify a question as out of scope before searching: the user only asks book questions, and a lite router refused a real one (2026-11-16). Search first; let <<none>> decide.
- A matched heading is not evidence by itself — always bring the paragraph under it.
- Don't name scratch scripts after packages (attr.py in %TEMP% shadowed the attrs package).

- BM25 lexical scores are normalised per query: the best weak match always looks strong. Do not use them as an absolute relevance threshold; let the model that read the passages pick related ones (<<none: n>>).

## Agent & GenAI upgrade session — 2026-11-17

**User request (Hinglish):** make the agent better at a bigger level, add Agent/GenAI features that
make it easy and detailed, directions for new users, auto-update Handsover.md / REPAIR_PROMPT when
the limit ends or work completes, an MD file for adding features, and docs good enough that another
AI can take over.

**Decisions and why**
- Follow-ups via a same-call `<<next:>>` marker (cloud) + outline fallback (local): zero extra
  requests on a ~20 req/day/model free tier.
- Answer styles as prompt notes, not separate pipelines: one code path, one audit.
- Chapter scope filters inside each retriever (BM25 `keep=` predicate on the cached full index,
  dense search widened ×12 then filtered) — no second index, no cache eviction.
- Stream read timeout 60 s for cloud: measured `gemini-3.5-flash` silent for the full 180 s on two
  live questions while `gemini-2.5-flash` then answered.
- Docs restructured around AGENTS.md (entry point for any AI) + CLAUDE.md (`@AGENTS.md` import),
  with FEATURES.md (catalog), ADD_FEATURE.md (recipes + prompt), USER_GUIDE.md (users),
  REPAIR_PROMPT.md (prompt + triage). History kept below each "HISTORY" marker, not deleted.
- Handover facts are machine-generated (`tools/handover_snapshot.py`, Claude Code Stop/PreCompact
  hooks) because sessions end without warning; narrative stays human/AI-written.

**Lessons**
- The Bash tool on this machine collapses `\\` in heredocs; use Write/Edit or script files.
- `pytest -q` from the root collected `backups/` tests and errored; fixed with `testpaths = tests`.
- First-visit Guide dialog would cover screenshots; `?guide=0` disables it, `?guide=1` forces it.

## Voice + directions session — 2026-11-17 (2)

User asked (Hinglish): UI in English by default; a popup to change language with arrow directions
("start conversation here", "library is here") in the chosen language; the mic could not be stopped
after an accidental tap; speech should first appear as text in the box, then be sent by the user.

- Root cause of the "mic won't stop" bug: a second tap while the browser's permission prompt was open
  started a second MediaRecorder (the `recording` flag was set only after `getUserMedia` resolved), and
  the stopped recording went straight to `/voice`, which ran a full (minutes-long) answer.
- Fix: one state machine (idle → starting → recording → transcribing), `POST /transcribe` (text only),
  Stop / Cancel / Esc, short-tap guard. Verified in the user's real Chrome with a stubbed recorder.
- Headless Chrome screenshots misplace elements near the sticky composer by ~100 px; real Chrome
  measured the tour spotlight exactly on the mic (8 px padding). Do not "fix" placement from headless.

## Loop 4 lesson — 2026-11-18
"Slow answers" after a restart were mostly cold search, not the model: retrieve 42.5 s of 65 s.
Measure the stages in `data/diagnostics/*.json` (`stages`, `explain.seconds`, `audit.seconds`) before
blaming a provider. Warm-up + longer cloud keep-alive brought retrieve to 3.25 s.
