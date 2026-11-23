# FEATURES.md — everything Mufti AI does, and where it lives

One row per user-visible capability. "Cost" = extra model calls per question (the scarce resource:
2 GB GPU locally, ~20 Gemini requests/day/model on the free tier). Keep this table current when you
add or change a feature (AGENTS.md §7).

## Answering

| Feature | What the user gets | Code | Cost | Since |
|---|---|---|---|---|
| Explanation answers (default) | Teacher-style Markdown: direct answer, sections, summary; 4 languages; adab (ﷺ) | `app/agents/explain_agent.py`, `app/llm/prompts.py` `EXPLAIN_RULES` | 1 call | 2026-11-16 |
| Page citations | `[n]` after every factual sentence; validated in code; same-page passages merged | `explain_agent.renumber`, `build_citations`, `page_aliases` | 0 | 2026-11-16 |
| **Two-tier fact-check** — strong judge first (`audit_strong`: gemini-2.5-flash only, 40 s, long answers split into parallel ≤18-sentence chunks), lite chain as fallback (25 s) | `explain_agent.audit`, `chunked_audit`, `router.models_for(only_preferred)`, `config.yaml task_models.audit_strong` | 1-3 strong calls (own quota) | **2026-11-18 loop 7** |
| **Citations for uncited sentences** — the judge names the supporting source; code appends `[n]` (existing sources only) or the sentence is fixed/removed | `AUDIT_RULES` UNCITED, `SCHEMAS[audit].add_citations`, `citations_for_uncited` | 0 (same call) | **2026-11-18 loop 7** |
| **Number check** — numbers/years (any script) that appear in no source are pointed out to the judge | `numbers_in`, `AUDIT_RULES` NUMBERS | 0 | **2026-11-18 loop 7** |
| **Quote check** — text in quotation marks (6+ words) that is not verbatim in the sources loses its quotation marks | `unquote_unverified` | 0 | **2026-11-18 loop 7** |
| Sentence-level fact-check (audit) | Unsupported/misattributed/overstated sentences fixed or removed; badge "Fact-checked" | `explain_agent.audit`, `AUDIT_RULES` | 1 lite call (cloud only, 25 s cap) | 2026-11-16 |
| Live streaming draft | Answer appears as it is written; replaced by the checked version | `router.stream`, `progress.draft_token`, `routes_chat` SSE `draft` | 0 | 2026-11-16 |
| **Answer styles** | Detailed / Short / Simple words / Study notes; same grounding | `explain_agent.STYLE_NOTES`, `ChatRequest.answer_style`, UI `#style` | 0 | **2026-11-17** |
| **Follow-up questions** | 3 "Ask next" chips under every answer | `app/agents/suggest.py`, `<<next: …>>` marker (cloud), outline fallback (local) | 0 (~40 tokens) | **2026-11-17** |
| **Same question, other style** | One-click re-ask: More detail / Simple / Short / Notes | `app.js` `nextSteps()` | 1 new question | **2026-11-17** |
| **Chapter focus (scope)** | Search only one chapter/section; honest fallback to whole library | `retriever_agent.run`, `hybrid.in_scope`, `bm25.search(keep=)`, `evidence.passes_floor` (`scope_hits`) | 0 | **2026-11-17** |
| **Topic suggestions for vague questions** | "kuch batao" → chapter topics to click | `formatter.next_questions`, `suggest.starter_topics` | 0 | **2026-11-17** |
| Second search before "not found" | `<<none>>` → one more search round | `graph.after_explain`, `expand_agent.py` | 1 call | 2026-11-16 |
| Honest outcomes | not in library / partial / OCR unreadable / service or quota failure — never conflated | `formatter.failure_reason`, `app/core/language.py` messages | 0 | 2026-11-12 |
| "Which book / reference?" card | Title, author, publisher, ISBN + pages of the previous answer, no model | `app/agents/bibliography.py` | 0 | 2026-11-16 |
| Script guard | Hindi answer mixed with Urdu script is regenerated once | `explain_agent.wrong_script_share` | ≤1 call | 2026-11-16 |
| Conversation memory | Follow-ups use the last turns; history saved per session | LangGraph SQLite checkpointer, `language_agent` rewrite | 0-1 call | 2026-11-11 |
| Strict claim pipeline (optional) | Older claim-by-claim verified answers | `answer_agent`, `verifier_agent`, `repair_agent`; `answer_mode='strict'` | 2-4 calls | 2026-11-13 |

## Models and reliability

| Feature | Code | Since |
|---|---|---|
| Cloud-first fallback Gemini → Claude → OpenAI → Ollama; UI shows selected vs actual model and why | `app/llm/router.py`, `routes_models.py`, `graph._fallback_reason` | 2026-11-11 |
| Gemini alternates + per-task lite models + daily-quota cooldown per model | `config.yaml` `gemini_alternates`, `task_models`; `router._route` | 2026-11-16 |
| **Search warm-up at server start** (corpus, BM25 index, bge-m3, Chroma) in the background; status in `GET /health` → `warmup` | `app/core/warmup.py`, `app/main.py` lifespan, `settings.warmup_on_start` | **2026-11-18 loop 4** |
| **Embedding keep-alive by mode** — 30 min when a cloud model answers, 5 min when the local model needs the GPU | `vector_store.embedding_keep_alive`, `config.yaml embedding_keep_alive_cloud/local` | **2026-11-18 loop 4** |
| **Frontend revalidation** — `Cache-Control: no-cache` on `/`, `.js`, `.css`, `.html` (ETag → 304), so updates reach the browser | `app/main.py` guard middleware | **2026-11-18 loop 6** |
| **Stalled-stream switch** (60 s without a chunk → next model; was 180 s) | `providers.stream_read_timeout`, `config.yaml` `stream_read_timeout` | **2026-11-17** |
| Circuit breaker for failing providers | `app/llm/circuit_breaker.py` | 2026-11-11 |

## Library, search and data

| Feature | Code | Since |
|---|---|---|
| PDF ingestion with Urdu OCR (Tesseract), per-page cache, quality audit | `app/ingestion/pdf_loader.py`, `ocr.py`, `indexer.py` | 2026-11-11 |
| Child-segment index (staged build → validate → activate → rollback) | `app/ingestion/segment_index.py` | 2026-11-12 |
| Hybrid search: bge-m3 dense + BM25 + keyword graph, RRF, concept lexicon | `app/retrieval/*`, `data/concept-lexicon.json` | 2026-11-12 |
| Chapter/section outline per book | `app/ingestion/book_tree.py`, `data/index/trees/` | 2026-11-13 |
| **Topic index** — sidebar ▦: 10 reviewed key concepts (4 scripts) + all 361 chapters/sections with page ranges; accent-insensitive, **cross-script** search (a matched concept adds its Urdu/Hindi forms, so "equality" finds مساوات sections); Explain / Summary / Focus; no model call | `suggest.topic_index`, `GET /topics`, `app.js` `loadTopics/renderTopics`, generic `views` table | **2026-11-18 loop 5** |
| **Chapter explorer API + UI** | `GET /books/{id}/outline` (`suggest.outline`), My library → ☰ Chapters | **2026-11-17** |
| Readability filter (OCR noise never shown/quoted) | `app/retrieval/evidence.py` `readable`, `legible_pieces` | 2026-11-13 |

## Interface

| Feature | Code | Since |
|---|---|---|
| Islamic emerald/gold UI, dark mode, RTL Urdu, mobile | `frontend/*` | 2026-11-16 |
| Source page viewer (OCR text, corrections, original PDF) | `app.js` `source()`, `/books/{id}/pages/{p}` | 2026-11-11 |
| **📷 Photo / 📎 file / drag & drop / Ctrl+V** — photo of a page (camera or folder), PDF (5 pages), .txt/.md → text read **locally** (Tesseract, Urdu Nastaliq `urd_naw`, Arabic, English, Hindi; EXIF rotation, contrast, upscaling) → editable card → **Explain this** (grounded pipeline) / **🔍 Find in my books** / Put in question box; re-read as another script | `app/core/extract.py`, `POST /extract`, `app.js` `handleFile`, camera dialog | **2026-11-18 loop 8** |
| **🔍 Find in my books** — which book and PDF page a passage or topic comes from, strong/possible/weak, View page / Explain this page (scoped); **no model call** | `POST /find` (`routes_attach.py`: expand_query → hybrid search → evidence.select) | **2026-11-18 loop 8** |
| Copy, Read aloud, Voice (local Whisper / browser) | `app.js`, `routes_voice.py` | 2026-11-11 |
| **Quiz me** — 2-6 multiple-choice questions from an answer's own cited sentences; each question links to its book page; answer-language UI; score | `app/agents/quiz_agent.py` (statements → one structured call → code checks: statement exists, correct option shares content words, no new numbers), `app/api/routes_quiz.py` (`POST /quiz`, answer loaded from server-side history), `config.yaml task_models.quiz` (lite models), `app.js` `runQuiz` (1 lite call, on demand) | **2026-11-17 loop 3** |
| **Saved answers (bookmarks)** — ☆ Save on any book answer; sidebar ★ Saved answers with search, open (Markdown + citations), download, two-step delete; survives conversation deletion; `data/saved/saved.json` (local, atomic writes, max 500) | `app/core/saved.py`, `app/api/routes_saved.py` (`POST/GET /saved`, `GET/DELETE /saved/{id}`), `app.js` `saveControl/loadSaved/openSaved` | **2026-11-17 loop 2** |
| **Download (.md) and Print/PDF of an answer** | `app.js` `downloadAnswer`, `printAnswer` | **2026-11-17** |
| **Guide dialog** (how to use, setup check, shortcuts; auto on first visit; `?guide=0/1`) | `index.html` `#guide-dialog`, `app.js` `openGuide` | **2026-11-17** |
| **Starter topics on welcome screen** | `GET /suggestions`, `app.js` `loadStarters` | **2026-11-17** |
| **Keyboard shortcuts** `/`, Alt+N, Alt+L, Alt+G | `app.js` keydown handler | **2026-11-17** |
| **English-by-default UI + welcome popup** choosing the *directions* language (English / Hinglish / Urdu / Hindi); header 🌐 button | `frontend/tour.js` (`T` translations, `showWelcome`, `setDirLang`), `app.js` `dirLang()` | **2026-11-17 (2)** |
| **Arrow tour** (spotlight + bubble with arrow, 9 steps incl. Topic index and Saved answers since loop 6, translated, RTL for Urdu, mobile opens the sidebar) | `tour.js` `startTour/showStep/placeTour`; URL `?tour=N`, `?lang=…`, `?guide=0/1` | **2026-11-17 (2)** |
| **Guide in the chosen language** (steps, setup-check summary/fix, shortcuts) | `tour.js` `renderGuide`, `app.js` `loadSetup` | **2026-11-17 (2)** |
| **Voice → text box → reader sends** (Stop / Cancel / Esc, accidental-tap guard, 60 s limit, one recording at a time) | `app.js` voice state machine (`startVoice/stopVoice/cancelVoice/finishVoice`), `POST /transcribe` in `routes_voice.py`, `stt.transcribe(language_hint)` | **2026-11-17 (2)** |

## Operations and handover

| Feature | Code | Since |
|---|---|---|
| **Answer feedback 👍/👎 + reasons** → `data/feedback/feedback.jsonl` (local); `GET /feedback/summary`; 👎 → unreviewed draft benchmark cases (`python -m eval.feedback_to_cases`) | `app/core/feedback.py`, `app/api/routes_feedback.py`, `app.js` `feedbackControls`, `eval/feedback_to_cases.py` | **2026-11-17 loop 1** |
| **Setup check / doctor** (English + Hinglish fixes) | `app/core/setup_check.py`, `.\doctor.ps1`, `GET /health/setup` | **2026-11-17** |
| **Auto handover snapshot** on Claude Code Stop / PreCompact | `tools/handover_snapshot.py`, `.claude/settings.json` | **2026-11-17** |
| Per-request diagnostic traces | `app/core/diagnostics.py` → `data/diagnostics/*.json` | 2026-11-12 |
| **Residual-error check** — re-judges FINAL answers with another strong model against their cited pages | `eval/residual_audit.py` (`--limit`, `--skip`, `--model`) | **2026-11-18 loop 7** |
| Answer benchmark | `eval/explain_eval.py`, `eval/book_benchmark.jsonl` | 2026-11-16 |
| MCP server for other AI clients | `mcp_server/server.py` | 2026-11-11 |

## API quick reference

`POST /chat` body:
```json
{"question": "Misaq-e-Madina kya tha?", "session_id": "my-session", "language_hint": "auto",
 "stream": true, "answer_style": "detailed|short|simple|points",
 "scope": {"book_id": "c2fd1e0906c9c087", "page_start": 70, "page_end": 76, "label": "Bones"}}
```
Response adds (2026-11-17): `followups: [str]`, `answer_style`, `scope: {…, "applied": bool}`.
Other new routes: `POST /transcribe` (audio → `{transcript, detected_language}`, never answers), `GET /health/setup`, `GET /books/{id}/outline`, `GET /suggestions?language=Hinglish`.
