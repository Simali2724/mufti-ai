# AGENTS.md — start here (for any AI: Claude, ChatGPT/Codex, Gemini, Cursor, Copilot…)

This file is the single entry point for an AI (or a new developer) taking over **Mufti AI**.
Read it fully before touching anything. It tells you what the project is, where everything
lives, which rules are non-negotiable, how to verify a change, and how to hand over when you stop.

> Owner context: the user writes in **Hinglish**, is not a programmer by profession, and wants
> answers from *their own Islamic books* explained completely, respectfully and with page
> references — "the way ChatGPT/Gemini explain", never a false "not found". Reply to them in
> simple Hinglish; keep code comments and docs in English.

---

## 1. What the project is (30-second version)

A private, local web app at **http://localhost:786** that answers questions about the PDF books
in `data/books/` (currently *Muqaddima Seerat-ur-Rasool* ﷺ, Urdu, 689 pages, scanned/OCR; and
*Creation of Man*, English, 102 pages).

```
question ─► language agent ─► router ─► hybrid search (bge-m3 vectors + BM25 + keyword graph)
         ─► evidence windows (readable book passages only)
         ─► explain agent: ONE streamed, cited Markdown answer  (Gemini → Claude → OpenAI → local Ollama)
         ─► audit: second model pass fact-checks every sentence; fixes/removes unsupported ones
         ─► formatter: answer + [n] page citations + follow-up questions ─► browser (SSE stream)
```

Stack: Python 3.12 · FastAPI · LangGraph · Chroma · rank-bm25 · Ollama (bge-m3 embeddings,
qwen3:1.7b local fallback) · Gemini free tier (main answering model) · vanilla JS frontend.
Hardware: Windows laptop, **2 GB MX450 GPU** — local generation is 2-3 tokens/s, so cloud
models do the real answering; Ollama must still run because search embeddings are local.

## 2. Reading order (do not skip)

| # | File | Why |
|---|---|---|
| 1 | **AGENTS.md** (this) | map, rules, protocol |
| 2 | **Handsover.md** — top auto-snapshot + "CURRENT STATE" | what is running, what changed last, what is next |
| 3 | **TASKS.md** — top "Open now" list | prioritised work |
| 4 | **Rules.md** | hard rules learned from real failures (grounding, adab, measurement) |
| 5 | **Architecture.md** — "At a glance" | modules, data flow, state keys |
| 6 | **FEATURES.md** | every user-visible feature → the code that implements it |
| 7 | as needed: **ADD_FEATURE.md** (build something new), **REPAIR_PROMPT.md** (fix something broken), **RUN_COMMANDS.md** (commands), **USER_GUIDE.md** (what users see), **Memory.md** (history of decisions), **VERIFICATION.md** (what was measured) |

## 3. Code map

| Path | What it does |
|---|---|
| `app/main.py` | FastAPI app, rate limit, local-origin guard, static frontend |
| `app/api/routes_chat.py` | `POST /chat` (SSE: `status`, `draft`, `draft_reset`, `done`), sessions |
| `app/api/routes_admin.py` | `/health`, `/health/setup`, `/books`, `/books/{id}/outline`, `/books/{id}/pages/{p}`, `/books/{id}/pdf`, `/suggestions`, `/ingest`, `/health/providers` |
| `app/api/routes_models.py` | `GET/PUT /settings/models` (no secrets ever) |
| `app/api/routes_voice.py` | `POST /voice` local Whisper → same pipeline |
| `app/agents/graph.py` | LangGraph wiring + `ask()` builds `ChatResponse` |
| `app/agents/state.py` | `AgentState` keys (the contract between agents) |
| `app/agents/bibliography.py` | "which book / author / reference?" answered from reviewed metadata, no model |
| `app/agents/language_agent.py` | reply language, follow-up rewrite, Urdu/English query variants |
| `app/agents/router_agent.py` | greeting / unsafe / needs_topic / search-everything |
| `app/agents/retriever_agent.py` | hybrid search + evidence selection; **chapter scope** with honest fallback |
| `app/agents/explain_agent.py` | **default answer path**: prompt, streaming, citations, audit, answer styles, follow-up marker |
| `app/agents/suggest.py` | follow-up questions & starter topics (model marker or book outline), outline API |
| `app/agents/expand_agent.py` | second search round before saying "not in the book" |
| `app/agents/formatter.py` | final text for every outcome (answered / partial / none / service failure) + history turn |
| `app/agents/answer_agent.py`, `verifier_agent.py`, `repair_agent.py` | older **strict** claim pipeline (`answer_mode='strict'`), kept and tested |
| `app/llm/prompts.py` | `EXPLAIN_RULES`, `AUDIT_RULES` and strict-mode prompts |
| `app/llm/router.py` | provider order, per-model alternates, quota cooldown, streaming fallback |
| `app/llm/providers.py` | raw HTTP for Gemini / Anthropic / OpenAI / Ollama, timeouts |
| `app/retrieval/hybrid.py`, `bm25.py`, `vector_store.py`, `evidence.py` | search and evidence windows |
| `app/ingestion/*` | PDF → OCR → pages → segments → Chroma; `book_tree.py` chapter outline |
| `app/core/config.py` + `config.yaml` + `.env` + `model-settings.json` | settings (see §6) |
| `app/core/setup_check.py` | new-user "doctor" (`.\doctor.ps1`, `/health/setup`) |
| `app/core/diagnostics.py` | per-request trace JSON in `data/diagnostics/` — read these when debugging |
| `frontend/index.html`, `app.js`, `style.css` | the whole UI (no build step) |
| `eval/explain_eval.py`, `eval/book_benchmark.jsonl` | answer-quality benchmark (60 reviewed cases) |
| `tests/` | offline pytest suite (mocked models) + `ui_markdown.test.js` |
| `tools/handover_snapshot.py` | rewrites the auto-snapshot block of Handsover.md |
| `mcp_server/server.py` | MCP tools: `search_books`, `get_page`, `list_books`, `ask_mufti` |
| `backups/<change>-<date>/` | copies of files before each substantial change |

## 4. Non-negotiable rules (full list in Rules.md)

1. **Grounding**: every factual sentence comes from book passages and carries a `[n]` citation
   validated in code. Never weaken `AUDIT_RULES`, citation checks or readability filters to make
   an answer "work". Fix by correcting/removing a sentence, not by refusing the whole answer.
2. **No false refusals**: search before refusing; `<<none>>` triggers one more search; keep
   "model could not explain" separate from "book does not contain this".
3. **Adab**: ﷺ after the Prophet's name, respectful tone, no sectarian judgement, refer personal
   rulings (fiqh) to a qualified scholar.
4. **Secrets**: never print, log, commit or send `.env` values. The UI only learns *whether* a key exists.
5. **Data**: never delete or rebuild `data/books`, `data/index`, `data/book-metadata`,
   `sessions.sqlite` to "fix" something. Segment index changes go build → validate → activate.
6. **Hardware**: never run an eval and the server against Ollama at the same time; long jobs use
   PowerShell `Start-Process … -RedirectStandardOutput` (Bash background jobs get killed).
7. **Honesty**: report what was measured with the artefact path; label simulated vs live;
   never mark untested work done.
8. **Back up** files under `backups/<name>-<yyyymmdd>/` before substantial edits.

## 5. Verify a change

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m pytest -q          # offline suite, ~10 s (testpaths = tests)
node --check frontend\app.js; node tests\ui_markdown.test.js
.\doctor.ps1                                      # environment / setup check
# live (needs Ollama + server running, uses Gemini quota ~2 calls per question):
.\.venv\Scripts\python.exe -u -m eval.probe "Misaq-e-Madina kya tha?" --mode gemini
```
Gemini free tier ≈ 20 requests/day **per model**; one question = answer + audit (+ rewrite).
Spend live calls deliberately.

## 6. Configuration layers (later wins)

`app/core/config.py` defaults → `.env` (keys, ports, flags) → `config.yaml` (model IDs, timeouts,
`gemini_alternates`, `task_models`) → `model-settings.json` (user's choice from the UI: mode, order,
model per provider). Answer path switch: `answer_mode` in `config.py` (`explain` | `strict`).

## 7. Handover protocol — MANDATORY before you stop

You may be cut off at any moment (usage limit, context limit, shutdown). Therefore:

1. **Automatic part** — `.claude/settings.json` runs `tools/handover_snapshot.py` on every
   Claude Code *Stop* and *PreCompact*. It refreshes only the block between
   `<!-- AUTO-SNAPSHOT:START/END -->` in Handsover.md (services, books, index, model mode, recent
   files, open tasks). Other tools/AIs: run it yourself:
   `.\.venv\Scripts\python.exe tools\handover_snapshot.py --tests`
2. **Your part, after every meaningful step (not only at the end)** — update in Handsover.md the
   section `# CURRENT STATE`: *what the user asked · what you changed (files) · what you verified
   (commands + results + artefact paths) · what is NOT done · exact next command*. Then tick/add
   items in TASKS.md "Open now". If you learned a lasting lesson, add it to Memory.md / Rules.md.
3. **When the task is complete** — also update FEATURES.md (if user-visible behaviour changed),
   USER_GUIDE.md (if users must do something new), VERIFICATION.md (what you measured).
4. **Obsidian (owner's second brain)** — the project is mirrored in the vault at
   `C:\Users\Moinuddeen hussain\Documents\Ali_second_Brain\Ali_second_Brain\00 - Dashboard\01 - Projects\Mufti AI\`
   (hub `Mufti AI.md` + Overview, Features, Accuracy, Architecture, Setup and Run, Test Results, Bugs and
   Fixes, Decisions, Work Log). After a completed change, add a dated Work Log entry and update Test Results
   and the hub's "At a glance" / review items. Facts only, no secrets, same format as the existing notes.
5. **Never** leave a half-applied edit undocumented: if you stop mid-change, write
   "IN PROGRESS: <file> <what remains>" at the top of CURRENT STATE.

## 8. Common tasks → where to look

| Task | Go to |
|---|---|
| Add a feature | ADD_FEATURE.md (recipes + copy-paste prompt) |
| An answer is wrong / refused / slow | REPAIR_PROMPT.md (triage table + copy-paste prompt) and the newest `data/diagnostics/*.json` |
| Add a book | RUN_COMMANDS.md → "Add a book" |
| Change models / keys | USER_GUIDE.md → "Models"; `config.yaml`; `.env` |
| Explain the app to the user | USER_GUIDE.md |
