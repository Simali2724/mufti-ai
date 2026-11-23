# AI handover — start here

<!-- AUTO-SNAPSHOT:START -->
## Auto-snapshot (machine-written — do not edit by hand)
_Refreshed 2026-11-24 00:15 by `tools/handover_snapshot.py`. Facts only; the narrative is in the sections below._

| Item | State |
|---|---|
| App server `http://localhost:786` | not running |
| Ollama `:11434` (needed for search embeddings) | not running |
| Books indexed | 2: Muqaddima-Seerat-ur-Rasool-1_1.pdf (689 p, 662 chunks); creation-man_1.pdf (102 p, 98 chunks) |
| Active segment build | 20261116-121031 (3784 segments, bge-m3) |
| Saved answering mode | gemini · openai=gpt-4.1-mini, anthropic=claude-sonnet-4-6, ollama=qwen3:1.7b, gemini=gemini-3.5-flash |
| Cloud keys configured (names only) | GOOGLE_API_KEY |
| Offline test functions | 228 in tests/test_*.py |
| Offline suite result (this snapshot) | 290 passed, 1 warning in 67.42s (0:01:07) |
| Open TASKS.md items | 51 |

**Recently changed source/docs (48 h):** `frontend/app.js` (11-24 00:08), `frontend/index.html` (11-24 00:07), `app/api/routes_chat.py` (11-24 00:07), `app/retrieval/vector_store.py` (11-24 00:07), `app/llm/providers.py` (11-24 00:06), `app/llm/router.py` (11-24 00:06), `app/llm/preferences.py` (11-24 00:06), `app/core/config.py` (11-24 00:03), `tools/prepare_cloud_deploy.py` (11-24 00:02), `tools/cloud_reindex.py` (11-24 00:02), `app/ingestion/indexer.py` (11-24 00:02), `app/ingestion/segment_index.py` (11-24 00:01), `app/core/setup_check.py` (11-24 00:00), `app/core/warmup.py` (11-24 00:00), `app/main.py` (11-24 00:00)

**Newest eval results:** `eval/residual-audit-before-3flash.json` (11-18 01:31), `eval/residual-audit-after.json` (11-18 01:29), `eval/residual-audit-before.json` (11-18 00:17)

**Newest request trace:** `data/diagnostics/20261123-120124-islamic-spain-se-arabic-science-europe-m.json`

**Newest backup:** `backups/cloud-deploy-20261123`

**Last open items in TASKS.md:**
- [ ] Review page-hit misses (`state-en-2`, `comp-en-1`, `seerah-*` expectations).
- [ ] Script-mixing guard for Hindi answers from lite models.
- [ ] Merge duplicate-page citations.
- [ ] Browser check when the Chrome extension is connected.
- [ ] Recommend a paid Gemini (or other) key to the user: free tier = 20 requests/day/model.
- [ ] Hinglish piety question misses page 51 (retrieval).
- [ ] Full 48-case rerun after quota reset (~13:30).
- [ ] Decide with the user: move OLLAMA_MODELS permanently to C: (D: drive unstable).
- [ ] Full 48-case rerun now that two books share retrieval (book-1 cases may pick up book-2 passages).
- [ ] Run the 60-case eval after the ~13:30 quota reset (stop the server first).
<!-- AUTO-SNAPSHOT:END -->
Filename intentionally matches the user's requested Handsover.md.

## How this file works (handover protocol — summary of AGENTS.md §7)
1. The block above is **machine-written** by `tools/handover_snapshot.py` (Claude Code hooks run it
   on every Stop and before context compaction; any AI can run it by hand, `--tests` also runs the suite).
2. `# CURRENT STATE` below is **written by the AI/human after every meaningful step**: request ·
   changes · verification with artefacts · not done · exact next command. If you stop mid-change,
   put `IN PROGRESS:` at its top. Move the previous CURRENT STATE down into HISTORY (newest first).
3. New to the project? Read AGENTS.md first. Fixing a bug? REPAIR_PROMPT.md. Adding a feature? ADD_FEATURE.md.

# LOOP STATUS — self-paced improvement loop (started 2026-11-17, Claude Code `/loop`)
The user asked: "aur feature dalo, loop pe set karo khud ko, Handover.md update, make this best".
Each iteration: one feature/fix from TASKS.md "Open now" / ADD_FEATURE.md backlog → backup → tests →
real-browser or live check → docs (this file, TASKS, FEATURES, VERIFICATION) → snapshot.
| Iteration | What | Verified | Backup |
|---|---|---|---|
| 1 | Answer feedback 👍/👎 + reasons → local JSONL → draft benchmark cases | 258 tests; real-Chrome flow | `backups/loop1-feedback-20261117/` |
| 2 | Saved answers (☆ Save, ★ Saved answers view, search, open, download, delete) | 261 tests; real-Chrome flow | `backups/loop2-saved-20261117/` |
| 3 | Quiz me (MCQs from the answer's cited sentences, code-checked, page chips) | 266 tests; live 4.6 s 3/4 kept; real-Chrome UI | `backups/loop3-quiz-20261117/` |
| 4 | First-question speed: background search warm-up + cloud embedding keep-alive 30 min | live retrieve 42.5 s → 3.25 s, total 65 → 41 s; 270 tests | `backups/loop4-warmup-20261118/` |
| 5 | Topic index (concepts + 361 sections, cross-script search, Explain/Summary/Focus) | 271 tests; real-Chrome search checks | `backups/loop5-topics-20261118/` |
| 6 | Tour/Guide cover new features in 4 languages; frontend `Cache-Control: no-cache` (stale tour.js found) | 272 tests; real-Chrome 4 languages | `backups/loop6-directions-20261118/` |
| 7 | ACCURACY: two-tier audit (strong→lite, parallel chunks), citations for uncited sentences, number hints, quote check, residual-error tool; fixed Gemini 400 + breaker cascade | 281 tests; live 3/3 audited; before/after residual NOT yet measured (Gemini overloaded) | `backups/loop7-accuracy-20261118/` |
| 8 | Photo / file / drag & drop / paste → local OCR → Explain (grounded) or 🔍 Find in my books (no model); urd_naw OCR; tour+Guide step | 289 tests; 4/4 pages found at rank 1; real-Chrome drop→find→explain | `backups/loop8-photo-file-20261118/` |
| 9 | Accuracy follow-up: residual judge made robust; real lite-audit misses found (2 of 7 flags real); second strong judge gemini-3-flash-preview | 290 tests; strong path blocked by free-tier 429 until reset | `backups/loop9-strong-fallback-20261118/` |
**Next candidates:** compare two books · conversation export (whole chat) · quota/model status panel.

# CURRENT STATE — 2026-11-24: Free Cloud Hosting (Render) & User API Key Support (complete, verified)

## What the user asked (Hinglish, summarised)
User wants to host Mufti AI for free to share a demo link with people. Raised two challenges:
1. How will public users access/use the AI API? (Solution: server key as default demo quota + optional user-provided Gemini API key in browser).
2. Prepare the code, repo, and deployment setup for their GitHub (https://github.com/Simali2724).

## What changed (backups: `backups/cloud-deploy-20261123/`)
| Area | Change | Files |
|---|---|---|
| Cloud Embeddings | Added Gemini Embedding API (`text-embedding-004`) support to replace local Ollama `bge-m3` in cloud mode | `app/retrieval/vector_store.py`, `app/core/config.py` |
| Cloud Execution | Dynamic `$PORT`, relaxed CORS for cloud origin, skipped origin-guard in cloud mode, optional Whisper/voice | `app/main.py`, `Dockerfile`, `start_cloud.sh`, `render.yaml` |
| User API Key | ContextVar `request_api_keys` populated from `X-Gemini-Key` header; UI input in Model dialog saved to `localStorage` | `app/llm/preferences.py`, `app/llm/router.py`, `app/llm/providers.py`, `app/api/routes_chat.py`, `frontend/index.html`, `frontend/app.js` |
| Re-indexing & Setup | Scripts for cloud re-indexing and setup checks with Ollama skipped in cloud mode | `tools/cloud_reindex.py`, `tools/prepare_cloud_deploy.py`, `app/core/setup_check.py`, `app/core/warmup.py` |
| Git repository | Safe `.gitignore` and `.dockerignore` ignoring secrets, local DBs, and logs; initial git commit on branch `main` | `.gitignore`, `.dockerignore`, `.env.example`, `render.yaml` |

## What was verified
- `node --check frontend/app.js; node tests/ui_markdown.test.js`: OK (exit code 0)
- `python -m pytest -q`: 290 passed in 58.8s (exit code 0)
- `tools/handover_snapshot.py --tests`: refreshed snapshot successfully
- Git commit created on branch `main` with 0 sensitive files tracked (no `.env`, no `sessions.sqlite`, no logs).

## What remains for user
1. Create a repository on GitHub (https://github.com/new) named `mufti-ai`.
2. Push local commits to GitHub using `git remote add origin ... && git push -u origin main`.
3. Create a free account on Render.com, select "New Web Service" → Connect GitHub repository → Enter `GOOGLE_API_KEY` → Deploy!
### Manual testing launch — 2026-11-23
User requested startup for manual testing. Started Mufti AI and Ollama in hidden processes; no application source, index or model settings changed. Verified HTTP 200 for /, /health (status ok, storage ok, two books), /settings/models (Gemini / gemini-3.5-flash selected, local_online=true), and Ollama /api/tags (bge-m3 and local answer models installed). Startup logs: logs/mufti-manual-20261123-114429.*.log and logs/ollama-manual-20261123-114429.*.log. No question was submitted and cloud answering/quota was not tested. Next step: open http://localhost:786 and test manually. Identify current listeners before restarting; do not rely on saved PIDs.

## What the user asked (Hinglish, summarised)
UI should stay English by default. A popup should let the user change the language, with arrow
directions ("start the conversation here", "the library is here") — English by default, and in the
chosen language once one is picked. The mic kept recording after an accidental tap and could not be
stopped; speech should first appear as text in the chat box and only then be sent.
(The user's message ended with "aur" — there may be one more request still to come.)

## What changed (backups: `backups/voice-tour-20261117/`)
| Area | Change | Files |
|---|---|---|
| Mic bug | Root cause: a second tap during the permission prompt started a second recorder; the stopped audio went to `/voice`, which ran a whole answer. Now a single state machine idle→starting→recording→transcribing; tap again/Stop finishes, Cancel/Esc discards, <0.7 s ignored, 60 s limit | `frontend/app.js` (voice block) |
| Speech → text box | New `POST /transcribe` returns only text; the UI appends it to the question box and the reader presses Send. `/voice` kept for API compatibility. Whisper gets the reply-language hint (Urdu/Hindi/English; Hinglish left to detection) | `app/api/routes_voice.py`, `app/voice/stt.py`, `app/main.py` (rate limit) |
| English UI | Hero, title, placeholder, chips, "Ask next", restyle buttons in English | `index.html`, `app.js` |
| Welcome popup + 🌐 | First visit: choose the directions language (English default / Hinglish / Urdu / Hindi) | `frontend/tour.js` (new), `index.html`, `style.css` |
| Arrow tour | 7-step spotlight tour with arrow card, translated, RTL Urdu, mobile sidebar handling, re-measured every 300 ms | `tour.js`, `style.css` |
| Guide | Rendered from translations; setup-check summary/fix in the chosen language; "Show the tour" button | `tour.js`, `app.js` |
| Tests/docs | `tests/test_voice.py` (+4); USER_GUIDE, FEATURES, REPAIR triage, Rules, Memory, VERIFICATION, Desgin, TASKS, RUN_COMMANDS | |

## Verified
- `pytest -q` **254 passed**; `node --check` app.js + tour.js; UI markdown test OK.
- Real Chrome (extension), mic stubbed: double-tap cancels with 0 recorders; normal take → text in box, `/transcribe` 1 call, `/chat` 0 calls; short tap, Cancel and Esc all discard. Welcome → हिन्दी → tour + guide all in Hindi. Spotlight measured exactly on the mic. Test localStorage keys removed afterwards, so the user will see the English welcome popup on next open.

## Not done / next
1. A real spoken test (Urdu + Hinglish) by the user through local Whisper.
2. Everything still open from the previous state below (latency re-measure with the 60 s stream timeout, 60-case eval, `/hooks` reload).
3. Ask the user what came after "aur".

## Service state
Ollama and the app server (:786) running hidden; server restarted after the backend change.

---

# PREVIOUS STATE — 2026-11-17: agent & GenAI upgrade (complete, verified)

## What the user asked (Hinglish, summarised)
Make the agent better "at a bigger level"; add Agent/GenAI features that make it easier to use
and give detailed information; add directions for new users; when the limit runs out or work is
complete, update Handsover.md and REPAIR_PROMPT; add an MD file for adding new features; enhance
all MD files so the whole project can be understood later and handed to another AI.

## What changed (backups: `backups/agent-genai-v2-20261117/`, originals of every edited file)
| Area | Change | Files |
|---|---|---|
| Answer styles | `answer_style`: detailed / short / simple / points — prompt note only, grounding & audit unchanged | `schemas.py`, `graph.py`, `state.py`, `explain_agent.STYLE_NOTES`, `routes_voice.py`, UI `#style` |
| Follow-up questions | Cloud model writes `<<next: q1 \| q2 \| q3>>` in the SAME call (0 extra calls); stripped before audit; validated; outline fallback for local / missing | `app/agents/suggest.py` (new), `explain_agent.py`, `formatter.next_questions` |
| Vague questions | `needs_topic` / `not_in_library` now suggest chapter topics | `formatter.next_questions`, `suggest.starter_topics` |
| Chapter focus (scope) | `ChatRequest.scope` restricts BM25/dense/graph/tree routes; small sections swept in page order; <2 hits → whole library with `scope.applied=false` | `retriever_agent.py`, `hybrid.py`, `bm25.py` (`keep=`), `evidence.passes_floor`, `expand_agent.py` |
| Stalled streams | Cloud stream read timeout 60 s (was 180 s) → next Gemini model sooner | `providers.stream_read_timeout`, `config.yaml stream_read_timeout` |
| New endpoints | `GET /health/setup`, `GET /books/{id}/outline`, `GET /suggestions` | `routes_admin.py`, `app/core/setup_check.py` (new) |
| UI | Guide dialog (how-to in Hinglish, Setup check, shortcuts; auto first visit, `?guide=0/1`); style selector; follow-up chips; "Same question" re-ask buttons; Download .md; Print; chapter explorer (Explain / Summary / Focus); focus chip; starter topics; shortcuts `/` Alt+N/L/G | `frontend/index.html`, `app.js`, `style.css` |
| Doctor | `.\doctor.ps1` / `python -m app.core.setup_check [--json]` — read-only checks with English + Hinglish fixes | `doctor.ps1`, `app/core/setup_check.py` |
| Handover automation | Auto-snapshot block; Claude Code hooks Stop + PreCompact | `tools/handover_snapshot.py`, `.claude/settings.json` |
| Docs | New: AGENTS.md, CLAUDE.md, USER_GUIDE.md, ADD_FEATURE.md, FEATURES.md. Restructured: REPAIR_PROMPT.md (prompt + triage), Architecture.md ("At a glance"), TASKS.md ("Open now"). Updated: README, Rules, Memory, RUN_COMMANDS (fixed corrupted `data\books` paths), VERIFICATION, Desgin, PRD | `*.md` |
| Tests | 19 new offline tests; `pytest.ini testpaths = tests` so plain `pytest -q` no longer collects `backups/` | `tests/test_agent_features.py`, `tests/ui_markdown.test.js`, `pytest.ini` |

## Verified
- Offline: **250 passed** (`pytest -q`, was 231); `node --check frontend/app.js` OK; `node tests/ui_markdown.test.js` OK (incl. half-streamed `<<ne` marker).
- `.\doctor.ps1`: all OK once Ollama was started (it correctly reported Ollama `[FAIL]` before, server `[WARN]`).
- Live over HTTP (server on :786, Gemini mode), scratch script `live_check.py`:
  - "Misaq-e-Madina kya tha?" **short** → 159 words, audited, 8 pages cited, 3 Hinglish model follow-ups, no marker leak, 117.7 s.
  - "Give a summary of “Development of Human Bones”" **points** + scope pp. 70-76 of *Creation of Man* → `scope.applied=true`, cited pages 71-75 only, audited (2 sentences fixed), 378 words, 207 s.
  - "mujhe kuch explain karo" → `needs_topic` + 3 chapter-topic suggestions, 11 s.
  - Both slow cases: trace shows `gemini-3.5-flash` **ReadTimeout after 180 s**, then `gemini-2.5-flash` answered — that finding produced the 60 s stream timeout (offline-tested; **not yet re-measured live**).
- UI screenshots (headless Chrome): `eval/ui-v2-guide.png`, `eval/ui-v2-answer-short.png`, `eval/ui-v2-answer-scoped-dark.png`, `eval/ui-v2-welcome.png`.

## Not done / next
1. Re-measure latency live with the 60 s stream timeout (expect ≈ 60-80 s instead of 180-210 s when 3.5-flash stalls):
   `.\.venv\Scripts\python.exe -u -m eval.probe "Misaq-e-Madina kya tha?" --mode gemini`
2. Consider moving `gemini-3.5-flash` behind `gemini-2.5-flash` if it keeps stalling (measure first).
3. Chapter explorer clicked through in a real browser (only headless screenshots + HTTP so far).
4. Full 60-case `eval.explain_eval` run is still outstanding from 2026-11-16 (stop the server first).
5. Claude Code hooks: `.claude/settings.json` was created in this session — the user may need to open `/hooks` once (or restart Claude Code) for them to load.

## Service state at handover
Ollama started hidden (`ollama serve`, model store `D:\ollama-models`); app server running on :786
(uvicorn, started hidden with `server-current.log` / `server-current-error.log`). See the auto-snapshot above.

---

# HISTORY (newest first)

# 2026-11-16: explanation mode

## What the user asked (in Hinglish, summarised)
Answer ANY question asked from the book; never refuse when the answer is in the book; explain
it well and with respect (religious material) the way ChatGPT/Gemini explain; industry level;
keep every doc (Handsover.md, REPAIR_PROMPT.md, …) current; change DB/RAG tech if it helps.
They also asked for continuous improvement in a loop (Chrome extension was mentioned, but no
browser tools were connected to the session — UI verified over HTTP + a headless DOM test).

## What was wrong
The default pipeline wrote ≤ 8 one-sentence claims (≤ 30 words each) and a verifier dropped any
claim it doubted, often down to a refusal. Saved preference was **Ollama-only (qwen3:1.7b on a
2 GB GPU)**, so every answer came from the weakest model at 2-3 tok/s.

## What changed (all backed up in `backups/explain-mode-20261116/`)
| File | Change |
|---|---|
| `app/agents/explain_agent.py` | **New default answer path.** Readable passages → one streamed, sectioned Markdown answer with `[n]` after every factual sentence → citation validation in code → sentence-level audit (fix or remove bad sentences) |
| `app/llm/prompts.py` | `EXPLAIN_RULES` (grounding, attribution, hedges, `<<full/partial/none>>`, format, adab/ﷺ, language/script) and `AUDIT_RULES` |
| `app/llm/providers.py` | `stream_complete` for Gemini (SSE), Ollama, OpenAI, Anthropic |
| `app/llm/router.py` | `_route`: per-model alternates (`gemini_alternates`), per-task preferred models (`task_models`), daily-quota cooldown per model, timeout → next model, audit never on local model, `stream()` |
| `app/llm/progress.py` | `draft_token` / `draft_reset` live-draft events |
| `app/api/routes_chat.py` | SSE `draft`, `draft_reset`, `status`, `done` |
| `app/agents/graph.py` | `retrieve → explain → (expand → explain) → format`; strict path kept behind `answer_mode='strict'`; answering model taken from the `explain` task |
| `app/agents/formatter.py` | Markdown outcome, `verification` = `audited` / `citations_checked`; `explanation_unverified` when no valid citation |
| `app/retrieval/evidence.py` | `legible_pieces`: line/script-level legibility so a readable sentence next to OCR noise is not lost (fixed comp-en-4) |
| `app/core/config.py` | `answer_mode`, `explain_audit`, `audit_local`; cloud evidence 12 windows / 12 000 tokens |
| `app/core/schemas.py`, `app/agents/state.py` | `answer_format`, `verification`, explanation state |
| `config.yaml` | default Gemini model `gemini-3.5-flash`; `gemini_alternates`; `task_models` (lite models for audit/rewrite/router/subtopics) |
| `model-settings.json` | **mode `gemini`, model `gemini-3.5-flash`, Ollama fallback** (was Ollama-only). Reversible in Models & fallback |
| `frontend/app.js`, `style.css` | Safe Markdown renderer, `[n]` citation chips opening the page, live drafting cursor, verification badge, copy button, friendly progress text |
| `eval/explain_eval.py` | **New** answer-stage benchmark (answered rate, false refusals, answered-absent, page hit, latency) |
| `tests/test_explain.py`, `tests/conftest.py`, `pytest.ini` | 19 new tests; existing graph tests pinned to strict mode |

## Measured (live, Gemini route, human-reviewed 48-case benchmark)
Full run, `eval/explain-eval-gemini.json` (before the last three fixes; mixed models because
free-tier quotas ran out mid-run and later cases used flash-lite models):
- answerable 42 → **answered 41 (0.976)**; false refusal: `comp-en-4` only
- page-hit rate of answered (≥ 1 cited page is a reviewed expected page): **0.854**
- absent 6 → answered anyway: `absent-ur-1`, `absent-hi-1` (both honestly said "not in the
  book" but were scored as answers); median latency **23.5 s**; 39 audited.

Targeted rerun after the fixes, `eval/explain-eval-rerun.json` (10 cases, gemini-3.5-flash-lite):
- comp-en-4 now answered from page 375; **all 4 absent cases correctly declined**;
  ge-en-1, ge-hi-1, piety-en-1, west-en-2, cm-hi-1 still answered; median 13.5 s.
- **A full 48-case run after the fixes has NOT been done yet** (free quota exhausted). Do it
  first after the daily reset: command below.

Live HTTP through the running server: Hinglish "Hijrat ke baad Madina mein…" → 44 draft events,
audited answer with 8 page citations in 20.8 s; follow-up "aur detail mein samjhao" in the same
session used the conversation (40 s); history reload keeps Markdown + citations.
Offline suite: **205 passed**. `node --check frontend/app.js` OK.

## Free-tier Gemini is the real constraint
`GenerateRequestsPerDayPerProjectPerModel-FreeTier` = **20 requests/day per model**. One
question = answer + audit (+ rewrite with history). The router now spreads load: answer on
`gemini-3.5-flash` → `gemini-2.5-flash` → `gemini-3-flash-preview` → lite models; audit and
rewrite on lite models first; a model that returned a daily 429 is skipped until its
`retryDelay`. ≈ 50 questions/day free. **A paid Gemini key (or an Anthropic/OpenAI key) removes
this limit and is the single biggest quality/reliability upgrade available.**

## Open items, in priority order
1. Full 48-case rerun after quota reset:
   `.\.venv\Scripts\python.exe -u -m eval.explain_eval --mode gemini --out eval\explain-eval-gemini-v2.json --delay 8`
   (stop the server first — shared 2 GB GPU).
2. Page-hit misses to review: `state-en-2` (expected 493), `seerah-*` (benchmark expects
   contents pages — re-review the expectation, do not tune for it), `comp-en-1`.
3. Lite models occasionally mix scripts in Hindi answers; consider a code-level script check
   with one regeneration.
4. Citations can list the same PDF page twice (two passages of one page); consider merging.
5. Browser check with the Chrome extension once it is connected to the session.

## Update 2026-11-16 (later): direct voice + "which book?" reference card
- User asked: explain anything in detail WITHOUT repeating "according to this book"; but when
  asked "kaun si book / reference kahan se", give the book name and all details.
- `EXPLAIN_RULES`: VOICE section (no "the book says / kitab mein likha hai"), detailed by
  default (350-900 words unless a single fact). `AUDIT_RULES`: direct voice is not misattribution.
- `bibliography.is_reference_question` + `reference_card`: title, author, publisher, first
  edition, ISBN (reviewed metadata, each with page) + pages of the previous answer. No model call,
  ~0.7 s, `verification='reviewed_metadata'`. Content questions containing "source"/"reference"
  ("source of law in Madinah") still go to the explanation path (content-word check).
- Graph resets `answer_format`/`verification` per turn (checkpoint state used to leak them).
- Live: Hinglish piety question -> 308 words, 0 "book says" phrases, audited; follow-up
  "ye kis book se hai?" -> card with pages 104/189. Suite: 217 passed.
- Loop item #1: that piety question did not retrieve reviewed page 51 (Hinglish wording).

## Loop iteration 1 — 2026-11-16 (attribution of quoted writers)
- The "piety question misses page 51" item was a false lead: page 51 defines Islam as personal
  piety (quoted from Western writers); it is not about the Prophet's ﷺ own worship, so the model
  was right not to use it for that Hinglish question.
- Real defect found in the trace: per-sentence legibility split initials, so quoted writers
  lost their names ("Cardinal R. W. Southern" -> "Southern", "Ronald L. Nettler" -> "Ronald L.").
  `evidence.legible_pieces` now keeps a readable line whole when its only unreadable pieces are
  name fragments (`name_fragment`). Corpus scan (1 541 parents): suspicious junk pieces 24 -> 18.
- Source notes now give full writer names (`explain_agent.quoted_writers`, incl. "X and Y"
  co-authors) and EXPLAIN_RULES says how to attribute footnoted quotations.
- Live: "What does the book say about personal piety and worship of God?" -> page 51, now
  attributed ("Western scholars … describe Islam as …"), audited, 14 s. Suite: 220 passed.

## UI + "ji haan, is kitab se" round — 2026-11-16
User asked: verified from the book, but say "yes, this book, from here" only when asked; explain
everything in more detail; make the UI a beautiful Islamic design everyone loves.
- **Reference card** (`bibliography.reference_card`) now opens with "Ji haan — yeh jawab isi
  kitab se liya gaya hai…" (4 languages, `CARD_LEAD`), repeats the previous question and lists
  its pages; Urdu section titles bidi-isolated (U+2068/2069); `coverage='full'` (was 'none', which
  made the UI say "No verified book answer").
- **More detail**: EXPLAIN_RULES asks for 450-1100 words with opening / background / one section
  per point with terms explained / examples & quotations with speakers / significance / summary,
  using every relevant source. Live: "Misaq-e-Madina kya tha? Tafseel se samjhao" -> 583 words,
  6 pages, audited, 27 s, 0 "the book says" phrases (was ~120-300 words).
- **UI redesign** (`frontend/index.html`, theme block at the end of `style.css`): deep-emerald
  sidebar with gold eight-point-star pattern, ivory page with faint girih pattern, mehrab
  (arch) hero with ﷽ in Amiri, Urdu tagline "علم کی روشنی، کتاب کے ساتھ", four starter questions
  (Hinglish/Urdu/English/Hindi), answer cards with gold top rule and ✦ headings, emerald user
  bubbles, gold citation chips, gold-ringed send button, night-emerald dark mode. Clean book title
  in UI (`niceTitle`), `?session=<id>` and `?theme=dark|light` URL parameters.
- Screenshots (headless Chrome): `eval/ui-welcome.png`, `eval/ui-welcome-dark.png`,
  `eval/ui-conversation.png`, `eval/ui-showcase.png`. Suite: 221 passed; `node --check` OK.

## Loop iteration 2 — 2026-11-16 ~11:40-12:10
- **Same-page citations merged** (`explain_agent.page_aliases`): passages from one PDF page share
  one citation number; the citation's full text joins both passages. (cm-en-5 showed page 350 twice.)
- **Script guard** (`wrong_script_share`, limit 0.15): a Hindi answer with Urdu script (or the
  reverse) is rewritten once with an explicit script note; the cleaner text is kept; recorded as
  `script_retry` in the trace. Costs a call only when it triggers.
- **Renderer**: indented lines under a numbered item stay inside that item and numbering
  continues (Gemini writes "1. **Title:**" + indented paragraph). New headless test
  `node tests/ui_markdown.test.js`.
- Live Hindi (UTF-8 body): "मीसाक़-ए-मदीना में ग़ैर-मुस्लिमों को क्या अधिकार…" -> 535 words, pure
  Devanagari (wrong-script 0.0), 7 distinct pages, audited (0 changes), 19.7 s, gemini-2.5-flash.
- Testing note: curl on Windows mangles non-Latin command-line JSON; send `--data-binary @file.json`.
- Suite: 223 passed. Full 48-case rerun still waits for the daily quota (main models reset ~13:30).

## Second book added — 2026-11-16 ~12:00-12:50: "Creation of Man"
- `data/books/creation-man_1.pdf`: "Creation of Man (A Review of the Qur'an & Modern Embryology)",
  Prof. Dr. Muhammad Tahir-ul-Qadri, ed. M. Asim Naveed, Minhaj-ul-Qur'an Publications, © 2001.
  102 pages, embedded English text (not OCR). Book id `c2fd1e0906c9c087`.
- Indexed additively (`app.ingestion.indexer`; book 1 skipped, untouched): 102 pages, 98 chunks.
  The 4 flagged pages (11, 19, 39, 56) were rendered and are publisher-logo divider pages.
- Segment build `20261116-121031` (3 784 segments / 759 pages, validate ok) **active**;
  previous `20261112-094445` kept for `rollback`.
- Reviewed metadata `data/book-metadata/c2fd1e0906c9c087.json`: title/author/editor (page 1),
  publisher/copyright 2001 (page 2), visually checked; plus a **reviewed outline** of 57 headings
  located in the page text and checked against the contents pages. `book_tree.reviewed_outline`
  uses it because the PDF's own outline is file names ("1.pdf"...). Tree: 9 chapters, 48 sections.
- Multi-book code: `display_title` (reviewed short titles in citations and UI), source headers
  name the book, EXPLAIN_RULES speaks of "the reader's library", author/title questions answer
  per book (or only the book the previous answer used), reference card lists only the books the
  previous answer used, `/books` returns `display_title` + `language`, UI cards no longer
  hard-code the first book.
- Live: Hinglish "Insaan ki takhleeq ke marahil…" 514 words, 10 pages of Creation of Man,
  audited; English Darwinian-evolution question 819 words, 9 pages, audited; "ye kis book se hai?"
  -> Creation of Man card; author question in context -> Creation of Man only; Urdu Misaq question
  on book 1 still 445 words from book 1. Screenshot `eval/ui-two-books.png`. Suite: 224 passed.

### D: drive incident during this work (important)
- Thousands of disk retry events (Event ID 153) at 11:51-11:55; `OSError Errno 22` on reads and
  writes; Ollama failed with "PrefetchVirtualMemory failed / model not found" because its model
  store is on D: (`OLLAMA_MODELS=D:\ollama-models`).
- Fix applied: Ollama restarted **for this session** with `OLLAMA_MODELS` pointing at the C: store
  (`%USERPROFILE%\.ollama\models`). Manifests of bge-m3 and qwen3:1.7b verified identical, and a
  fresh embedding equals the cached vector (cosine 1.0). The user-level env var was NOT changed:
  after a reboot Ollama will use D: again unless the user changes it.
- Code hardened: embedding-cache writes retry and then skip (`vector_store.cache_write`);
  `indexer.save_json` retries atomic writes.

## Fix — "Tissues and Body Form explain this in detail" refused (2026-11-16 ~13:00)
User report: the answer is on Creation of Man printed page 69 (PDF 73), yet the app replied
"I could not find sufficient verified evidence". Three separate defects, all fixed:
1. **Router refused before searching.** No rule matched, so a flash-lite model classified the
   question `out_of_scope` and the library was never searched. `model_router: false` (new setting):
   unsure questions are searched across ALL books; only the explicit rule lists (greeting, unsafe,
   obvious non-book topics) skip search. Saves ~1.5 s per question too.
2. **Heading-only evidence window.** The search matched p.73's 113-char heading; the 900-char cap
   in `evidence.window_text` skipped the 821-char paragraph under it. A heading (< 200 chars) now
   pulls its following paragraph up to 1 800 chars (`HEADING_WINDOW_CAP`).
3. **Short clean English lines dropped** ("Tissues and Body Form", "muscular system."), because
   `readable` needs four 4-letter words. `evidence.short_clean_latin` keeps them; corpus junk scan
   unchanged (47 suspicious pieces with or without the rule).
Plus: the audit is bounded (`audit_timeout: 25` s) — a flash-lite audit had taken 53 s.
Live after the fix: the exact question -> 312 words, pages 73 (+8), audited, **16.8 s** (was 71 s
before the audit bound); Hindi bones/muscles question 530 words p.72-75; Urdu flesh-on-bones
question 283 words p.72-75. Suite: 228 passed.

## Loop iteration 3 — 2026-11-16 ~13:05
- Added 12 human-reviewed Creation of Man cases (`com-*`) to `eval/book_benchmark.jsonl` (now 60),
  each case with a `book` id; `eval/explain_eval.py` scores page hits per (book, page) because page
  numbers repeat across books, and reports citations from other books. Expected pages read from the
  page text: seven chemical stages p.40-41, water p.42, Darwin p.18/22, Adam p.33, fertilization
  p.64, viability p.77, six-month pregnancy p.78, spermatozoa 1677 p.62, religion vs science p.12,
  tissues p.73, salsal p.45/47; absent: cloning ("clon" occurs in neither book).
- Evaluation deferred until the ~13:30 Gemini quota reset so it measures gemini-3.5-flash.

## Fix — irrelevant "related passages" for off-topic questions (2026-11-16 ~13:30)
User report: "write me a code of addting two number in C" returned "The indexed book does not
directly answer…" plus three unrelated pages (amino acids, World Order, star names) — it looked
like hallucination.
- **Programming requests** are recognised by rule (`router_agent.OUT_OF_SCOPE`: "write … code",
  "code likho", C++/Python/Java/HTML/SQL…, "… in C"): instant (~3.5 s) polite `OUT_OF_LIBRARY`
  reply naming the books, no search, no passages. Book questions such as "Code of conduct in the
  Charter of Madinah" or "Write about the life of the Prophet" still search.
- **Related passages are chosen by the answering model**, not by score thresholds: on no answer
  it replies `<<none: 2, 5>>` naming same-subject sources, or plain `<<none>>`. Score thresholds
  failed because BM25 is relative (the best weak match — "chain" in an amino-acid chain — scores
  high). Plain `<<none>>` -> new outcome `not_in_library` with `NOT_IN_LIBRARY` ("I searched every
  book in your library … none of them discusses this"), no passages. Score threshold
  (`truly_related`) still guards the strict pipeline.
- Related/excerpt blocks use reviewed book titles.
- Live: bicycle chain -> not_in_library, 0 passages; C code -> out_of_scope, 3.5 s; Karbala ->
  not_in_library; control "Darwin ke nazariye…" -> 713 words, Creation of Man pages. 231 tests.

## Service state at handover
App on http://127.0.0.1:786 (find the listener: `Get-NetTCPConnection -LocalPort 786 -State Listen`),
Ollama on 11434 (needed for bge-m3 search embeddings even in cloud mode). **Ollama is currently
running from the C: model store** (`$env:OLLAMA_MODELS="$env:USERPROFILE\.ollama\models"`) because
D: was failing; after a reboot it will use D:\ollama-models again unless the user changes it.

---

Checkpoint: 11 November 2026, Asia/Kolkata. This file is a durable continuation record, not a claim of universal answer coverage.

## Goal and current request
User reports weak/no answers, wants the selected/running model clearly visible, and wants all book-supported questions answered. Maintain strict source grounding. Finish retrieval/model visibility fixes, run tests and real book checks, and leave the local app running. User requested seven documentation files including this one.

## Start commands (PowerShell)
```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 786 --no-access-log
```
Open http://localhost:786. If Ollama is not already running, run `ollama serve` in another terminal. Do not start a duplicate service. Verify GET /health and GET /settings/models. If port 786 is occupied, identify the owning process before stopping it. Do not reuse a PID recorded in old chat history.

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m pytest tests -q
node --check frontend/app.js
```
The Codex restricted shell sometimes hung using D:'s Python; an authorized escalated run completed correctly. If D: disappears, reconnect/check it. Do not recreate data based on an absent mount.

## Read in order
Memory.md -> TASKS.md -> Architecture.md -> PRD.md -> Desgin.md -> Rules.md -> VERIFICATION.md. RUN_COMMANDS.md contains normal operation and cloud key setup. Real configuration is .env, config.yaml and model-settings.json. Never print .env.

## Data and prior evidence
PDF D:\Muqaddima-Seerat-ur-Rasool-1_1.pdf is indexed under data/books. Catalog: 689 pages, 662 passages, 28 unreadable/review pages. Preserve all data/index stores. Prior live English question about personal piety/worship produced verified PDF-page-51 citations; prior Hindi/Urdu broad questions refused. Full multilingual coverage is not proven. Prior iteration had 77 offline tests, real Gemma structured output and mocked cloud exhaustion; real clouds untested without keys.

## This checkpoint's source changes
app/llm/progress.py adds ContextVar-based request status callbacks. router.py reports actual attempts/skips/failures. graph.py isolates callback lifecycle and returns execution/reason metadata. routes_chat.py streams model status via a per-request queue. formatter.py saves citations/model executions/reason in new history entries. language_agent.py excludes metadata from outgoing history prompts. schemas/state include new fields.
query_expansion.py adds common Prophet-name aliases. hybrid.py retains a wider candidate pool before reranking; verifier_agent.py can request one alternate evidence batch if no direct answer was drafted. Exact quote and semantic verifier checks remain active. frontend/app.js/index.html/style.css show selected models, live running model, diagnostic reasons and retained response metadata.

## If interrupted now
Implementation has been written with source backups under backups/improvements-*. Current validation is in progress; inspect TASKS.md and any appended results below. Run tests before claiming completion. Test `Who is Mahomet explain` and the known page-51 question in English. A refusal must record the actual reason and model, not invent an answer. Inspect live response execution, reason_code, retrieved_count, citations and source page if it fails. Browser-check the selected-model strip after save/reload and actual running status. Record actual results here, including failures.

## Resume protocol
At every work stop, append: timestamp, changed files, exact tests/results, current server state, unresolved issue, and first next command. Copy this project directory with data if moving machines; exclude .env from anything shared with an AI service. Recreate .venv from requirements.txt on another machine. Preserve local data backups. Never rely on chat history as the only record.

## Verified checkpoint during improvement run
- Regression suite: 77 passed; four new improvement tests: 4 passed (81 total). JavaScript syntax passed.
- Real screenshot question `Who is Mahomet explain`: grounded=true, Gemini 2.5 Flash, PDF pages 201 and 234. Output saved in eval/improvement-live.json.
- Real Gemini requests now work with the user-configured key; a later connection failure exercised fallback to Qwen through Ollama. Never print that key.
- Background server started successfully and /health returned ok. Do not assume launch PID is the final Python child PID.
- UTF-8 interface text was repaired after a Windows default-codepage read; all further reads/writes must specify encoding=utf-8.
- Known page-51 question and browser history reload are still running at this checkpoint; final results will be appended.

## Final stopping point — improvement completed
- The app is serving http://localhost:786 from D:/mufti-ai. Background launch used hidden Start-Process; identify the current listener rather than trusting an old PID.
- Both live CLI book checks passed with citations; results in eval/improvement-live.json.
- Who is Mahomet explain | grounded=True | pages=[201, 234] | 102.0s | model=gemini-2.5-flash.
- What does the book say about personal piety and worship of God? | grounded=True | pages=[51] | 377.4s | model=gemini-2.5-flash.
- Browser test additionally verified real Gemini generation, actual Gemini 429 fallback, Ollama router/verifier, a cited page-51 answer, and successful history reload with model details/citations.
- Browser proof: answer-verification.jpg. Selected Gemini and actual per-agent model names are visible. UTF-8 was visually rechecked after reload.
- 81 offline checks passed (77 existing plus 4 new); final JavaScript syntax passed.
- Routine frontend refresh now reads local /settings/models instead of repeatedly querying cloud provider health.
- Immediate requested work is complete. Next work: manually annotate a multilingual book benchmark, measure retrieval/answer coverage, improve OCR and investigate multi-minute fallback latency. Concurrent local requests can cause expensive model switching; evaluate whole-question queuing on this small GPU. Do not weaken verification to force universal coverage.
- First next command: cd D:/mufti-ai; run .venv/Scripts/python.exe -m pytest tests -q, then inspect TASKS.md and eval/improvement-live.json.

## Latest checkpoint: author-question repair
The user reported `Who is author of Muaddima seerat ur Rasool` failing. Root cause: title/publication pages 2/3 visually name the author, but OCR corrupts the name; semantic retrieval and exact verification were a poor path for simple publication facts.

Visually confirmed from the uploaded PDF:
- Author: Dr. Muhammad Tahir-ul-Qadri, PDF page 3.
- Publisher: Minhaj-ul-Quran Publications, PDF page 2.
- ISBN: 969-32-0552-9, PDF page 3.
- First publication: February 1995, PDF page 3.

Records live in data/book-metadata/46a52585612a906c.json and include review provenance and the PDF SHA-256. Preserve this directory; a changed PDF invalidates the record. Raw OCR and the PDF were not edited.

New app/agents/bibliography.py runs before language/router. It matches narrow bibliographic intents and book titles, checks current PDF identity, and emits cited facts and saved history directly. Other questions retain the normal pipeline. The interface identifies verified book details and explains that no model generation was needed. Source details distinguish the reviewed transcription from raw OCR. Failed generated drafts are labelled as attempted drafts rather than successful answers.

Changed files: bibliography.py, graph.py, state.py, schemas.py, core/language.py, frontend/app.js and tests/test_bibliography.py. Source backups: backups/bibliography-*. A full suite passed 98 tests; the later Auto-language fix passed the 23-case focused bibliography/language suite, giving 99 distinct passing cases. JavaScript syntax passed. Six live API responses are stored in eval/bibliography-live.json (about 0.5–0.9s), and the exact screenshot question was observed in the browser with page 3.

An automatic approval review was interrupted by usage limit before the last restart and documentation update. On the user's continuation, review succeeded; no server was responding, so the current source was started again. Do not trust old PIDs; read server-current-error.log and check the actual listener. Final continuation checks are recorded below.

Next quality work: create a manually annotated body-text benchmark; inspect OCR for failed questions; measure retrieval recall and local-model output accuracy. This fixes the demonstrated author/publication failure; it is not proof that every substantive book question is answered correctly. Never weaken source verification just to increase answer coverage.


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
## New user-reported failure: gender equality (diagnosis and prompt only)
The user requested an explanation and repair prompt after `Explain Gender Equality in detail` returned no direct answer. No runtime implementation changes were made in this diagnosis turn. See REPAIR_PROMPT.md for the implementation brief.
Visually inspected physical PDF pages 50 and 257: page 50 explicitly discusses gender equality and quotes Inglehart/Norris; page 257 includes No Gender Discrimination in Adult Franchise. Both are indexed. This supports a scoped book-based response, not a claim that the book answers every aspect of the broad topic. Preserve attribution and inspect adjacent context.
Confirmed code constraints: answer_agent.py passes only three passages as short fragments and permits two claims; structured.py enforces this output ceiling; verifier_agent.py still accepts/rejects the draft as a whole. Full-context retrieval, partial coverage, per-claim verification and human-reviewed multilingual evaluation remain required. Existing test counts do not prove answer coverage. The screenshot used llama3.2:3b as fallback; inspect current saved preferences/traces instead of assuming the previously selected Qwen is still active.
Next action: implement REPAIR_PROMPT.md, beginning with reproducing the exact failed question and tracing candidate versus selected passages. Do not hardcode answers for these pages or overwrite the source PDF/index.

## Recovery checkpoint — 2026-11-12, resumed after an unplanned laptop shutdown
The machine lost power at about 00:04 on 2026-11-12, during the first run of the new
benchmark. Nothing below is a coverage claim. Measured results are appended as produced.

### State found on resume
- The coverage repair described in REPAIR_PROMPT.md had been written but never validated.
  No benchmark result file existed. Ollama and the app were both down.
- New since the pre-repair backup `backups/book-coverage-20261112/`:
  `app/retrieval/evidence.py`, `app/core/diagnostics.py`, `app/ingestion/segments.py`,
  `app/ingestion/segment_index.py`, `data/concept-lexicon.json`, `eval/book_benchmark.jsonl`,
  `eval/run_benchmark.py`, `eval/baseline_retrieval.py`.
  Changed: answer_agent, formatter, graph, language_agent, retriever_agent, router_agent,
  state, verifier_agent, routes_admin, routes_models, config, core/language, schemas,
  prompts, providers, llm/router, structured, hybrid, query_expansion, config.yaml,
  frontend/app.js, frontend/style.css and six test files.

### Done in this session
- Regression suite: one failure, `test_get_exposes_key_presence_without_secret_values`, which
  predated the `provider_state` field added by repair step 7. The field is deliberate, so the
  test was corrected rather than the code. Added two regressions asserting that a configured
  key is not labelled ready and that quota and cooldown states are reported distinctly.
  Also fixed cross-test pollution from the router's module-global `_outcomes` store.
  **Final: 122 passed.** `node --check frontend/app.js` passed.
- Restarted Ollama. `D:/ollama-models` has bge-m3:latest, qwen3:1.7b, gemma3:1b, llama3.2:3b.
  The app was not running; port 786 and 11434 had no listener. Do not trust any recorded PID.
- Restarted the interrupted retrieval benchmark over all 48 cases including hold-outs.

### Measured and observed so far
- Gemini returns a real HTTP 429 on every language-agent call in this run, so each case falls
  back to local qwen3:1.7b. That is the reason a retrieval-only pass takes tens of minutes.
  This is real provider quota exhaustion, not a simulated failure.
- At least one answerable case misses at the candidate stage, not only at the window stage:
  the Constitution of Madinah question with reviewed page 257 retrieved none of its expected
  pages. Recorded as a genuine retrieval miss to chase, not an acceptable result.

### Main unfinished item — the staged segment index is NOT active
`data/index/segments/20261111-234724/` holds only a partial `chroma/` directory. There is no
`segments.json` and no `active.json`, because the build was embedding segments when the power
failed. With no active build `segment_index.load_segments()` returns `[]`, `page_parents()`
returns `[]` and `search_segments()` returns `[]`. Retrieval is therefore still running on
page-level chunks, and the child-segment and parent-paragraph design of repair steps 2 to 4
is contributing nothing to the numbers currently being measured. Treat the retrieval figures
from this run as the page-level baseline, not as the repaired pipeline.

The extraction audit itself did complete: all 689 pages scored, 181 flagged
(28 empty, 91 fragmented tokens, 55 no English layer, 10 control characters, 5 very short),
saved to `data/index/extraction-audit.json`.

### Next steps, in order
1. Let the running retrieval benchmark finish; keep it as the page-level number.
2. Rebuild, validate and activate the segment index. The live page index is not touched and
   `rollback` reverses the activation:
   ```powershell
   cd D:\mufti-ai
   .\.venv\Scripts\python.exe -m app.ingestion.segment_index build
   .\.venv\Scripts\python.exe -m app.ingestion.segment_index validate --build-id <id>
   .\.venv\Scripts\python.exe -m app.ingestion.segment_index activate --build-id <id>
   ```
3. Re-run `python -m eval.run_benchmark --retrieval --holdout` and compare with step 1 and
   with `python -m eval.baseline_retrieval` for the replayed old pipeline.
4. Run `python -m eval.run_benchmark --answers`, then manually review the gender-equality
   answer against physical PDF pages 50 and 257, keeping the Inglehart and Norris attribution
   distinct from the author's own conclusions.
5. Start the app on port 786, verify `/health` and `/settings/models`, browser-check the
   provider status strip and a live answer, and save evidence.
6. Update Architecture.md, Desgin.md, Memory.md, PRD.md, Rules.md, TASKS.md, VERIFICATION.md
   and RUN_COMMANDS.md with the measured results, including the failures.

**First next command if interrupted again:** `cd D:\mufti-ai`, confirm Ollama is listening on
11434, then run the segment index build in step 2. Do not rebuild or overwrite the live page
index, the reviewed book metadata or the saved conversations. Never print .env.

### Added after the checkpoint above (same session)
- Found that every file in `data/diagnostics/` had been written by the offline suite with
  mocked models, not by real requests, so none of it was evidence about live behaviour.
  `app/core/diagnostics.py` now resolves its output directory through `directory()` with an
  `override`, and the new `tests/conftest.py` redirects traces to a temporary path for the
  whole suite. Verified: the file count in `data/diagnostics/` is unchanged by a full run.
  The 25 mocked traces were moved to `backups/mocked-diagnostics-20261112/`, so
  `data/diagnostics/` is now empty and will hold only real request traces.
  Suite still 122 passed.

## Remaining verification checklist — written 2026-11-12 00:36
Nothing in this section has been verified yet. The implementation is written; the evidence
is not. Work top to bottom: item 2 blocks items 3 to 8. Tick an item only after seeing the
real output, and record the actual result, including failures, under this list.

### 0. Preconditions on resume
```powershell
cd D:\mufti-ai
# Ollama must be listening before anything else. Start it only if nothing answers:
curl.exe -s --max-time 5 http://127.0.0.1:11434/api/tags
ollama serve          # separate terminal, only if the call above returned nothing
.\.venv\Scripts\python.exe -m pytest tests -q        # expect: 122 passed
node --check frontend/app.js
```
Do not trust any PID in these documents. Check the listener.

### 1. Was the interrupted retrieval benchmark finished?
A run was started at 00:09 on 2026-11-12 over all 48 cases and had reached 38 when this list
was written. It may have finished, been killed by the session ending, or died with the
machine. Check `eval/benchmark-retrieval.json`. If it is missing or its `summary.cases` is
below 48, the run did not finish; re-run it:
```powershell
.\.venv\Scripts\python.exe -m eval.run_benchmark --retrieval --holdout
```
This number is the PAGE-LEVEL baseline, because the segment index is not active. Label it
that way. Expect roughly 45 seconds per case: every language-agent call hits a real Gemini
429 and falls back to local qwen3:1.7b.

### 2. BLOCKER — build, validate and activate the segment index
Until this is done, `load_segments()`, `page_parents()` and `search_segments()` all return
empty and repair steps 2 to 4 contribute nothing to any measurement.
```powershell
.\.venv\Scripts\python.exe -m app.ingestion.segment_index build
.\.venv\Scripts\python.exe -m app.ingestion.segment_index validate --build-id <id>
.\.venv\Scripts\python.exe -m app.ingestion.segment_index activate --build-id <id>
.\.venv\Scripts\python.exe -m app.ingestion.segment_index status
```
Pass condition: `validate` returns `ok: true` with no issues, and `data/index/segments/active.json`
exists naming that build id and the `bge-m3` embedding model. Delete nothing: the abandoned
partial build `20261111-234724` can stay, and `rollback` reverses an activation. The live
page index must not be rebuilt or overwritten.

### 3. Re-measure retrieval and compare three numbers honestly
```powershell
.\.venv\Scripts\python.exe -m eval.run_benchmark --retrieval --holdout --out eval/benchmark-retrieval-segments.json
.\.venv\Scripts\python.exe -m eval.baseline_retrieval
```
Compare: replayed old pipeline (`eval/benchmark-baseline.json`), page-level current
(`eval/benchmark-retrieval.json`), segments active (`eval/benchmark-retrieval-segments.json`).
Report `candidate_recall`, `window_recall`, `top3_recall` and the `misses` list for each.
A known miss to chase: the Constitution of Madinah case missed its reviewed page 257 at the
CANDIDATE stage, so no amount of reranking or windowing can recover it. If recall does not
improve, say so; do not re-tune thresholds until the numbers explain why.

### 4. Capture a real diagnostic trace of the failing question
`data/diagnostics/` is now empty on purpose and the test suite no longer writes there, so any
file appearing in it is a real request. Ask `Explain Gender Equality in detail` through the
running app, then read the newest trace and record: rewritten queries, candidate pages,
selected windows, model at each stage, timings and the rejection or coverage reason.

### 5. Run the answer pass
```powershell
.\.venv\Scripts\python.exe -m eval.run_benchmark --answers
```
Hours on the local model. Record `answered_rate`, `false_refusal_rate`,
`answered_absent_topic_rate`, `citation_page_accuracy`, `citations_verbatim_rate`,
coverage counts and latency. A false refusal on an answerable question and an answer on an
absent topic are both failures.

### 6. Manual review of the gender-equality answer — the point of the whole brief
Read the returned answer against physical PDF pages 50 and 257 in the original PDF. Check:
the answer is scoped to what the book actually supports; the Inglehart and Norris material on
page 50 stays attributed to them and is not presented as the author's own conclusion; page
257 is read inside its adult-franchise section; missing aspects are stated rather than filled
in; every claim carries a citation that is verbatim on the cited page. Automated
`grounded: true` is not a pass. `eval/rejected-book-quality-example.json` is the reminder of
why: it was grounded and still wrong.

### 7. Live provider behaviour and browser verification
Start the app and leave it running:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 786 --no-access-log
```
Check `GET /health` and `GET /settings/models`. In the browser confirm the provider strip
shows the real `provider_state` labels, not a blanket Ready, and that a quota or embedding
failure is never shown to the reader as absence of book evidence. Exercise the configured
cloud route and the Ollama fallback and state plainly which failures were REAL and which were
simulated. Save a screenshot as evidence, as was done for the author fix.

### 8. Documentation still to update
Only Handsover.md and REPAIR_PROMPT.md have been updated. Still to do once there are real
numbers: Architecture.md, Desgin.md, Memory.md, PRD.md, Rules.md, TASKS.md, VERIFICATION.md,
RUN_COMMANDS.md. Record measured failures, not just successes, and do not claim universal
coverage while measured failures remain.

**First command next time:** `cd D:\mufti-ai`, confirm Ollama answers on 11434, check whether
`eval/benchmark-retrieval.json` exists, then start item 2.

## Coverage repair — measured session, 2026-11-12 (09:00–13:00 Asia/Kolkata)

This section records measured numbers, including the failures. It is not a coverage claim.
Earlier sections remain valid history. **Read "Honest state of the answer stage" below before
telling the user that anything works.**

### What was blocking everything: the segment index was never active
`data/index/segments/` held only interrupted partial builds, so `load_segments()` returned
`[]` and retrieval ran on page-level chunks. Repair steps 2-6 contributed nothing to any
measurement taken before today.

Rebuilt, validated and activated:
- Active build `20261112-094445`: 3338 child segments over 661 pages, embedding model `bge-m3`.
- `data/index/segments/active.json` names it. `validate` returns `ok: true` with no issues.
- The live page index was never rebuilt or overwritten. `rollback` reverses the activation.
- Abandoned partial builds left in place on purpose: `20261111-234724`, `20261112-091359`,
  `20261112-091509`, `20261112-091648`.

`validate` caught a real chunker bug on the first complete build: `children()` folded a short
trailing remainder into the previous child *including the carried overlap*, duplicating a
sentence and breaking the child-in-parent invariant (2 of 3338 segments). Fixed in
`app/ingestion/segments.py`; now 0 of 3338 offenders, and no parent loses a single word.
`validate` also used to `break` at the first offender; it now reports all of them.

### Retrieval: measured before/after over all 48 benchmark cases (42 answerable)

| | OLD pipeline replayed | segments + content-word variant |
|---|---|---|
| candidate_recall | 0.810 | **0.881** |
| reviewed page reaches the answering model | **0.643** | **0.810** |
| misses at the answer stage | 15 | **8** |

Files: `eval/benchmark-baseline.json` (old pipeline), `eval/benchmark-retrieval-content.json`
(current), `eval/benchmark-retrieval-segments-norewrite.json` (segments without the
content-word variant), `eval/benchmark-retrieval-segments-rewrite-on-partial.json` (partial
run with the model rewrite on).

The exact failing question now retrieves correctly. `Explain Gender Equality in detail` puts
reviewed pages **50 and 257 as evidence windows 1 and 2** in about 2.6 seconds, page 50
matching on its clean English layer (relevance 0.73, lexical 1.0). Under the old pipeline page
50 ranked fourth and was cut by the three-passage limit, which is what the brief suspected.

A new auditable query variant does most of the work. A long natural question dilutes BM25: its
few high-information words are outvoted by the many low-information ones. Measured on this
book, `sanitation` alone ranks the right page first, while the same word inside
`What does the book say about sanitation and street lighting in Madinah?` did not place that
page in the top 30 at all. `query_expansion.content_query()` now searches the question's own
content words as one additional variant tagged `content_words`. It introduces no
book-specific term and removes nothing from the original query. It fixed `state-en-1` (page
492 to rank 1), `state-en-2` (493), `state-en-3` (487) and the held-out `cm-en-7` (257).

Of the 8 remaining misses, 3 (`author-en-1`, `author-ur-1`, `pub-en-1`) are bibliographic
questions that `app/agents/bibliography.py` answers *before* retrieval runs, so they are not
real failures of the live app; the retrieval-only harness bypasses that agent. The real
content misses are `cm-hi-1`, `cm-en-6`, `seerah-en-1`, `seerah-ur-1`, `seerah-hg-1`.

**Benchmark ground-truth problem, not fixed.** `seerah-en-1/ur-1/hg-1` expect pages 14, 17, 26
and 28. Those pages were inspected: they are table-of-contents and heading-list pages (page
17's entire English layer is `i ii iii iv v i ii iii`). They carry the topic words but no prose
that could support a claim, so ranking them higher would hurt answer quality. These three
expectations need re-reviewing against the book's actual prose before their recall number
means anything. Do not tune retrieval to satisfy them.

### The model query-rewrite was removed for local models, on measurement
On the 29 cases that ran both ways, window recall and top-3 recall were **identical** (24/29
and 23/29) while total retrieval time fell from **1102 s to 106 s**. Each rewrite cost 90-144 s
because it forces an embedding/chat model swap on the 2 GB GPU, and the local 3B model's
translations were corrupt: Devanagari inside Urdu output, and Cyrillic characters in a
transliteration of "sovereignty". `app/agents/language_agent.py` now rewrites only when there
is conversation context to resolve, or when a cloud model is actually available and therefore
cheap. Setting `model_rewrite_without_history = True` forces the old behaviour back.

### Honest state of the answer stage — THE REMAINING PROBLEM
Retrieval is fixed. **Answer generation on this hardware is not, and that is a capability
limit rather than a bug left unfixed.**

Measured on this machine (NVIDIA GeForce MX450, **2 GB** VRAM, confirmed via
`Win32_VideoController`):
- qwen3:1.7b is fully GPU-resident (1.44 GB) and still generates at **1.6-3.0 tokens/s**.
- A sectioned answer is 600-900 output tokens, so one answer call takes **215-580 s**.
- Reducing `num_ctx` from 8192 to 4096 did **not** help. Output length is what costs.

Five defects were found and fixed at this stage. Each one on its own produced "no answer":

1. **Claims past #8 were silently discarded.** The answer schema allows up to 20 claims
   (5 sections x 4) but the verifier schema caps `claim_id` at 8, so every later claim received
   no verdict and was rejected for "No verdict returned for this claim". Verification now runs
   in batches of `answer_max_claims` with ids renumbered inside each batch. Regression:
   `tests/test_improvements.py::test_long_answer_claims_are_all_verified_in_batches`.
2. **The expand round destroyed the first round's evidence.** `expand_agent` selected windows
   only from newly retrieved candidates and excluded the pages already shown, so a question
   whose answer was found in round one lost that page the moment a second round ran. Observed
   live: pages 50 and 257 were found, then replaced by 260/601/207, and the reader was told the
   book does not answer the question. It now ranks both rounds together. (`graph.keep_best` is
   still dead code.) Regression: `test_expand_round_keeps_the_first_rounds_evidence`.
3. **The expand round crashed the whole request.** `diagnostics.record('expansion', queries=...,
   **report)` raised `TypeError: got multiple values for keyword argument 'queries'`, because
   the retriever report carries its own `queries` key. Any question needing a second round
   failed outright. Regression: `test_expand_round_records_diagnostics_without_crashing`.
4. **Every local answer call was killed at 180 s.** `provider_timeout` was a single value, so a
   legitimate 215-580 s local generation was cut off and the reader saw "No answering model
   could be reached", which reads as absence of book evidence. `app/llm/providers.py` now uses
   `config.yaml: ollama_timeout: 900` for local and keeps 180 s for cloud.
5. **The JSON schema grammar tripled generation time.** llama.cpp expands `maxLength` into GBNF
   repetition. Same model, same prompt, same 634 output tokens, same 10 resolvable claims:
   full schema **394 s (1.6 tok/s)**; schema with length and count bounds stripped
   **215 s (3.0 tok/s)**. Dropping the schema entirely was faster still but produced **0**
   resolvable claims, so the structure is required and only the bounds are expensive.
   `app/llm/structured.py: relax_for_grammar()` strips them from the local grammar only, and
   `answer_agent.attach_support` now enforces the section count, claim count, heading length
   and claim length in code instead of trusting the model.

Also fixed: each passage was sent to the answer model **twice** (as `passage` and again as
numbered `spans`), so the real prompt was about double the computed token budget; and BM25
rebuilt its tokenised index over all 3338 segments on every query variant, now cached with a
content-derived key (`app/retrieval/bm25.py`, with a staleness regression test).

Evidence is now sized to the model that will actually answer. Measured on the same question:
8 windows / 2400 tokens took 492 s, while 6 windows / 1500 tokens took 215 s and produced MORE
resolvable claims (10, from pages 50, 257 and 280). `evidence_windows` / `evidence_token_budget`
apply locally; `evidence_windows_cloud` / `evidence_token_budget_cloud` apply to a cloud model.

### The gender-equality answer: manually reviewed, and it FAILED review
This is the point of the whole brief, so read it carefully.

With llama3.2:3b, the model saved in `model-settings.json` at the start of the session, every
claim was rejected and the user got no answer. With qwen3:1.7b the app returned
`grounded: true, coverage: partial`, citing pages 280, 50 and 257 in 339 s. **That output was
checked by hand against the PDF and it was wrong:**

- Claims [1]-[3] cited **page 280**, whose span reads `آینی مساوات کا حق` — the right of
  *constitutional* equality among the Charter of Madinah's parties, which is a different
  concept. The claims asserted "The Quran and Hadith explicitly state that men and women are
  equal in rights and responsibilities" and "guarantees equal human rights for both genders".
  **Neither statement appears in that span.**
- The page-50 claim dropped the **Inglehart and Norris** attribution and presented their quoted
  view as the book's own conclusion — precisely what the brief forbids.
- The page-257 claim welded "Conditional Superordination of State" to gender equality.

So `grounded: true` was a **false positive**: a 1.7B verifier approved a 1.7B drafter's
fabrications. This is the same failure class as `eval/rejected-book-quality-example.json`.
Automated grounding remains untrustworthy on this hardware.

Two **code-checkable** guards were added rather than relying on model judgement. Verification
was made stricter, never weaker:

- **Concept guard.** When the question matches a reviewed lexicon concept, the span a claim
  rests on must carry one of that concept's reviewed surface forms, in any script. The lexicon
  already separates `gender_equality` from `constitutional_equality`; verification now uses
  that. It does not apply when no concept matched, so ordinary questions are unaffected.
- **Attribution guard.** `quoted_authorities()` recognises the book's own "Surname, Title, p. N"
  citation form. If a window credits an outside writer, a claim drawn from it must name them.
  `evidence_payload` now also tells the model which writers a passage quotes, so a small model
  does not have to infer it from a garbled citation line.

Also: a claim is no longer discarded merely for lacking a final full stop. Punctuation is
presentation, not evidence, so `verifier_agent.terminate()` closes the sentence with the
script's own full stop. A claim that genuinely trails off in a connector is still rejected.

After these guards the same question returns `reason_code: unsupported_claims`, with pages 50,
257 and 282 offered as **related material to read**, never as a verified answer. The trace
`data/diagnostics/20261112-123001-explain-gender-equality-in-detail.json` records the four
rejections: two for missing Inglehart/Norris attribution, one for resting on a different
concept's span, and one model non-entailment verdict.

**That is the correct behaviour and it is still not an answer.** The honest conclusion: the
retrieval, evidence, coverage and verification machinery is correct and demonstrated, and a
1.7B-3B local model cannot draft a properly attributed, concept-correct claim that survives
honest verification. `tests/test_evidence_ranking.py` demonstrates that a well-formed
attributed claim ("Inglehart and Norris describe gender equality as the main fault line.")
passes both guards, so a capable model plus this same evidence would answer correctly.
**Gemini returns a real HTTP 429 on every call** — verified directly this session — so that
could not be demonstrated.

### Not done
- **The `--answers` benchmark pass over all 48 cases was NOT run.** At 340-550 s per case it is
  4.5-7 hours on this machine. There is therefore no measured `answered_rate`,
  `false_refusal_rate`, `answered_absent_topic_rate` or `citation_page_accuracy`. Do not quote
  any such number; none exists. Run it overnight:
  `.\.venv\Scripts\python.exe -u -m eval.run_benchmark --answers --holdout --out eval/benchmark-answers.json`
- **No browser check and no screenshot this session.** `/health`, `/settings/models` and a live
  `/chat` call were verified over HTTP, but the UI was not opened in a browser.
- The concept and attribution guards have not been measured against the whole benchmark, so
  their false-refusal cost is unknown. The attribution guard is deliberately conservative: it
  demands attribution for every claim drawn from a window that credits an outside writer
  anywhere in it, which may over-reject.
- The `cm-hi-1` and `cm-en-6` retrieval misses are unexplained.
- The three `seerah-*` benchmark expectations point at contents pages and need re-review.

### Environment facts worth keeping
- GPU: NVIDIA GeForce MX450, 2 GB, plus Intel Iris Xe. Local generation is 1.6-3.0 tok/s.
- `model-settings.json` was changed this session from `llama3.2:3b` to **`qwen3:1.7b`**, because
  llama3.2:3b (2.02 GB) does not fit the 2 GB GPU and produced only rejected fabrications.
  Change it back in **Models & fallback** if desired; it is a preference file, not a secret.
- Only `GOOGLE_API_KEY` is set in `.env`, and it is quota-exhausted (real 429). `.env` was
  never printed.
- A long run started from the Bash tool is killed when its background shell is reaped. Use
  PowerShell `Start-Process ... -RedirectStandardOutput` for anything over a few minutes. Two
  benchmark runs were lost this way, at 29/48 and 6/48 cases.
- D: reported "The device is not ready" once mid-session and recovered by itself. Check the
  drive before concluding that data is lost.
- Source backup for this session: `backups/claim-loss-20261112/`.

### App state at the end of this session
Serving `http://localhost:786`, started hidden with uvicorn. The launch pid was 5504 but the
actual listener was **13628** — identify the listener, never trust a recorded pid. Ollama is
listening on 11434, started manually this session, so its output is not in the Ollama app's
own `server.log`. Suite: **131 passed**. `node --check frontend/app.js` passed.

### First commands on resume
```powershell
cd D:\mufti-ai
curl.exe -s --max-time 5 http://127.0.0.1:11434/api/tags             # Ollama must answer first
.\.venv\Scripts\python.exe -m app.ingestion.segment_index status      # expect 20261112-094445 active
.\.venv\Scripts\python.exe -m pytest tests -q                         # expect 131 passed
Get-NetTCPConnection -LocalPort 786 -State Listen                     # find the real listener
```
Then start the overnight `--answers` pass, because every answer-stage number is still missing.
Do not rebuild the live page index, the reviewed book metadata or the saved conversations.

### Final live verification through the running server — 2026-11-12 13:29
Question: `Explain Gender Equality in detail`, asked over HTTP against the app on port 786 with
the user's saved settings (Ollama only, qwen3:1.7b). Saved: `eval/ge-live-http.json`.
Trace: `data/diagnostics/20261112-132957-explain-gender-equality-in-detail.json`.

```
seconds   : 66.3          (was 866 s before this session's fixes)
grounded  : False
coverage  : none
reason    : unsupported_claims
answering : ollama / qwen3:1.7b
evidence  : [50, 257, 282, 286, 14, 280]
citations : []
related   : [50, 257, 282]
```

The answering model drafted 8 claims and **all 8 were rejected by the code guards alone**, so no
verifier model call was even needed — which is why the request now takes 66 s rather than many
minutes. Breakdown from the trace:
- 2 claims from page 50 rejected: `Quoted outside view stated without its attribution to
  Inglehart, Norris, Pippa, Ronald`. Those two claims were otherwise on the right page with the
  right concept; the model simply would not name the writers, although `evidence_payload` now
  tells it explicitly that the passage quotes them and that a claim must name them.
- 6 claims from pages 280 and 286 rejected: `Cited span carries a different concept than the
  question asked about` — constitutional equality and women's protection rights, not gender
  equality.

The reader is shown page 50's clean English sentence about gender equality and page 257's adult
franchise line as **related material to read**, with working page links, and is told plainly
that the book does not directly answer the question. That is honest and useful, and it is not
the verified scoped answer the brief asked for.

**One sentence from the model would have produced a correct answer.** `tests/test_evidence_ranking.py`
shows that "Inglehart and Norris describe gender equality as the main fault line." passes both
guards on the real page-50 text. The retrieval, evidence, coverage, citation and verification
machinery is therefore demonstrably correct end to end; the gap is the local model's ability to
write an attributed, concept-correct claim. With Gemini quota-exhausted (real 429) that could not
be demonstrated this session.

### Latency, before and after, same question
| | before | after |
|---|---|---|
| retrieval to evidence windows | page-level, page 50 cut by the 3-passage limit | **2.6 s**, pages 50 and 257 as windows 1 and 2 |
| full request through the server | 866 s, or HTTP 500 at 179 s | **66 s** |
| answer model call | 467-584 s, killed at the 180 s timeout | ~57 s at 6 windows / 1500 tokens / relaxed grammar |


---

# Handover — 2026-11-13: the answer stage, repaired

## Read this first

The previous checkpoint concluded that the pipeline was "demonstrably correct end to end" and
that the only remaining gap was "the local model's ability to write an attributed,
concept-correct claim". **That conclusion was wrong**, and acting on it would have meant
buying a bigger GPU to fix three code defects. The gender-equality question now answers.

What was actually broken, in the order it mattered:

1. **There was no targeted claim repair anywhere in the graph.** The brief requires a rejected
   claim to be repaired from its own evidence before being abandoned. The only recovery route
   was `expand`, which re-searches the entire book and redrafts the whole answer — useless for
   the measured failure, where retrieval and evidence were already correct and one sentence was
   missing two words. `app/agents/repair_agent.py` is new.
2. **The attribution guard was window-wide.** Every sentence of a paragraph containing a
   footnote had to credit that footnote's author. The brief says attribution attaches to the
   quoted span; it now does, by citation position.
3. **The verifier contradicted itself.** It returned `answers_question=false` while its own
   feedback for the same claim read *"The claim is fully entailed by the span."* That verdict
   now gates only questions that demand a relation (why/when/who), which is where it carries
   information.

## What works now

- **The acceptance case passes.** On `gemini-2.5-flash` the question returns a correctly
  attributed, correctly scoped explanation citing pages 50 and 257 in 47 s, preserving the
  Inglehart/Norris attribution, the source's "could plausibly" hedge, and the page-257 claim's
  scope (adult franchise, not gender equality in general). Full text in VERIFICATION.md,
  saved in `eval/ge-gemini.json`.
- **On the local 1.7B model** the same question returns either a verified partial answer with
  correct attribution, or the new `explanation_unverified` outcome showing the book's own
  excerpts, clearly labelled as excerpts. **Neither claims the book has no answer** — which is
  what it used to do, wrongly, about material printed on page 50.
- **Retrieval is unchanged at its best-ever numbers**: candidate 0.881, window 0.810, top-3
  0.738 over all 48 cases. The answer-stage work cost nothing in retrieval.
- **167 tests pass**, 41 of them new and each written from a real failure.
- MCP `search_books` was raising `TypeError` on every call and is fixed; `list_sections`,
  `get_section` and `locate_page` added over the new tree.

## Files changed

| File | Change |
|---|---|
| `app/agents/repair_agent.py` | **New.** Targeted per-claim repair; deterministic attribution needs no model call |
| `app/agents/verifier_agent.py` | Span-scoped attribution; three-way concept guard; relevance scoping; new grounding-floor, copied-span, dropped-hedge, one-sentence and bibliography-only guards; machine-readable rejection codes; verified claims carried across repair rounds |
| `app/agents/graph.py` | `repair` node wired between `verify` and `expand` |
| `app/agents/answer_agent.py` | Claims carry their section heading; adjacent-concept sources marked with a caution |
| `app/agents/formatter.py` | `explanation_unverified` / `insufficient_evidence_after_search` outcomes; excerpts show the span that concerns the question |
| `app/retrieval/evidence.py` | Three-way concept relation; soft adjacent-concept cap; same-page paragraph recovery; list-aware span splitting; clean tree headings |
| `app/ingestion/book_tree.py` | **New.** Book/Chapter/Section/page-range tree from the PDF outline, with staleness detection |
| `app/retrieval/tree_nav.py` | **New.** Bounded navigation route over clean titles; off by default on measurement |
| `app/retrieval/hybrid.py` | Optional third retrieval route |
| `app/llm/prompts.py` | `REPAIR_RULES`; hedge preservation; a worked negative example drawn from a real fabrication |
| `app/llm/structured.py`, `app/core/config.py`, `app/core/language.py`, `app/core/diagnostics.py` | Repair schema, new settings, attribution/fallback wording, new reason codes |
| `mcp_server/server.py` | `search_books` fixed; section tools added |
| `frontend/app.js` | Copy for the three new reason codes |
| `eval/run_benchmark.py` | Resumable `--answers`, `--windows`, `--delay`, `--mode` override, concept-aware selection |
| `eval/probe.py` | `--mode` override; concept-aware selection |
| `tests/test_answer_quality.py`, `tests/test_book_tree.py` | **New**, 36 tests |

## What is NOT done — read before claiming anything

- **No complete answer-stage benchmark exists.** Not for this session and not for any previous
  one. Do **not** quote an `answered_rate`, `false_refusal_rate`, `answered_absent_topic_rate`
  or `citation_page_accuracy`: none is measured over the full 48 cases. What exists is 3 cloud
  cases (`eval/benchmark-answers-gemini-partial.json`) and however many local cases the run
  below has completed.
- **A local full pass was left running** and writes `eval/benchmark-answers-local.json` after
  every case. **Resume it, do not restart it.**
- **`ge-ur-1` is a measured false refusal** and the single most valuable lead. The question
  asks in correct Urdu (`صنفی مساوات`); page 50's wording is `نوعی مساوات`. The lexicon has
  both and retrieval finds the page, so the failure is at the answer stage. Even Gemini failed
  it. Start here.
- **No browser screenshot.** The Chrome extension was not connected. The UI was verified at the
  HTTP layer the browser uses, and the new reason codes are present in `frontend/app.js`, but
  nobody has looked at it.
- **Gemini free-tier quota is exhausted again** after ~5 questions. It does reset — the
  previous session's "permanent 429" was a quota window. Pace cloud runs with `--delay`.
- `cm-hi-1` and `cm-en-6` retrieval misses remain unexplained.
- The three `seerah-*` benchmark expectations still point at contents pages and need
  re-reviewing against the book's prose. **Do not tune retrieval to satisfy them.**

## The hardware problem that cost hours

**D: is an external SSD and it disconnected repeatedly.** At its worst Windows logged **6,653
disk I/O errors in twenty minutes**; the source PDF and every `.md` document became unreadable
and the server died mid-request with `OSError: [Errno 22] Invalid argument: '.env'`. None of
that is an application fault.

- `Get-ChildItem` happily lists files whose contents cannot be read. A directory listing is not
  proof the drive is healthy. Use the read test in RUN_COMMANDS.md.
- A **complete working backup is at `C:\mufti-ai-salvage`** (source, venv, active segment
  index, book, 392 MB). The test suite passes from it unchanged, so it can be used directly if
  D: is unavailable again.
- Ollama also wedged once after hours of heavy 2 GB-GPU work: a request hung for 12 minutes
  while the server process sat idle. Restart `ollama serve` when that shape appears.

## Service state at handover

- App served from `D:\mufti-ai` on `http://127.0.0.1:786`. **Find the listener, never trust a
  recorded pid:** `Get-NetTCPConnection -LocalPort 786 -State Listen`.
- Ollama on 11434 with `qwen3:1.7b`, `bge-m3`, `llama3.2:3b`, `gemma3:1b`.
- Segment build `20261112-094445` active and untouched. Book tree built:
  `data\index\trees\46a52585612a906c.json`, 9 chapters, 301 sections, 0 problems.
- `model-settings.json` unchanged: Ollama-only, `qwen3:1.7b`. The cloud runs used a per-process
  `--mode` override and did not alter your saved preference.

## First commands on resume

```powershell
cd D:\mufti-ai

# 0. Is the drive actually healthy? Thousands of errors means reseat it first.
(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='disk'; StartTime=(Get-Date).AddMinutes(-20)}).Count

curl.exe -s --max-time 5 http://127.0.0.1:11434/api/tags          # Ollama must answer first
.\.venv\Scripts\python.exe -m app.ingestion.segment_index status  # expect 20261112-094445 active
.\.venv\Scripts\python.exe -m pytest tests -q                     # expect 167 passed
Get-NetTCPConnection -LocalPort 786 -State Listen                 # the real listener
```

Then, in priority order:

1. **Resume the local answer benchmark** (never restart it):
   `.\.venv\Scripts\python.exe -u -m eval.run_benchmark --answers --holdout --resume --out eval\benchmark-answers-local.json`
2. **Diagnose `ge-ur-1`**:
   `.\.venv\Scripts\python.exe -m eval.probe "صنفی مساوات کے بارے میں کتاب میں کیا لکھا ہے؟"`
   Retrieval finds page 50; watch the drafting and verification stages, not the search.
3. Open `http://localhost:786` and look at it.

Do not rebuild the live page index, the reviewed book metadata or the saved conversations.

## Follow-up fix, same day: unreadable excerpts and topicless questions

Reported from real use. The reader asked **"muje kuch explain karo"** and was shown this, under
a **Sources** heading, as the book's own words:

```
[1] PDF page 310 (printed 309) — «vii h V g ujo f ujo f ujo f»
[2] PDF page 626 — «o F o F i Zi F o F mF o F i i F o o F o m ]m B o mF m F B mF m F j o o»
[3] PDF page 297 (printed 29) — «i u h v ]i oF v ii u h v C v M o MV L L O EMD N u r o MV S P N O p QV L N O»
```

Two independent defects, both now fixed. Trace:
`data/diagnostics/20261113-160141-muje-kuch-explain-karo.json`.

### 1. The question named no subject, and was searched anyway

"muje kuch explain karo" is "explain something to me". It names nothing to look up. The app
searched regardless, matched legacy-font OCR noise on three unrelated pages, spent **224
seconds** drafting six claims, and rejected all six.

The guards did their job — nothing fabricated reached the reader — but the whole request was
waste. `router_agent.names_a_topic()` now checks whether the reader named any subject at all,
using the question's content words or a matched lexicon concept. A single word is enough
("mujhe seerat ke bare mein batao" names seerat), and a matched concept counts even when the
wording is pure scaffolding. With no subject the app asks which topic is meant, in the
reader's language, with examples from this book. **Measured: 224 s to 0.7 s.**

The Hinglish stopword list was missing `muje`, `mujhe`, `kuch`, `karo`, `samjhao` and similar,
which is why "muje kuch karo" had looked like a content query.

### 2. Unreadable OCR was presented as quotations from the book

The source PDF uses legacy InPage fonts and OCR over them produces glyph runs. These passed
every check in the pipeline — they are text, they tokenise, they match queries — so they
reached the reader as the book's own words. That is worse than saying nothing.

`evidence.readable()` now judges a passage: Urdu and Hindi by script density and the
isolated-single-character signature of broken Nastaliq OCR, Latin by whether real words of
four or more letters make up a reasonable share. Validated against the real corpus and the
exact strings above.

- **Displayed text is filtered.** `best_span`, `related_block` and `excerpt_block` only ever
  show a readable span, and a window with no readable span is skipped entirely.
- **Ranking demotes, it does not drop** (`UNREADABLE_FACTOR = 0.4`). This book's
  Western-writer quotations sit in paragraphs that are part real English and part glyph soup;
  discarding those would lose the material the `west-en-*` questions are about.
- **New outcome `extraction_problem`**, which the brief requires to be distinct. When the
  matched pages exist but nothing in them extracted readably, the reader is told exactly that
  and given the page numbers to open in the PDF — not a fabricated quotation, and not a claim
  that the book is silent.

### Known limitation, deliberately not fixed here

`spans_for` splits on sentence terminators and a glyph run contains none, so a run that sits
immediately before a real sentence merges into that span and rides along in the excerpt. The
span still reads as real text overall, so the reader is not misled, and the fully-unreadable
case that actually reached a reader is filtered. Separating junk *inside* a span means
changing span segmentation, which moves retrieval boundaries across the whole corpus and must
be measured against the benchmark first. Covered by
`tests/test_readability.py::test_known_limitation_junk_sharing_one_span_with_real_text_is_not_separated`.

### Verified after the fix

| Check | Result |
|---|---|
| `muje kuch explain karo` | `needs_topic`, **703 ms**, asks which topic, no citations, no excerpts |
| `mujhe seerat ke mutalea ki ahmiyat ke bare mein batao` | still searches; 6 windows, pages 353/71/8/46/6/66 |
| `Who is the author of this book?` | still grounded, 421 ms, cited to page 3 |
| Suite | **185 passed** (18 new in `tests/test_readability.py`) |
