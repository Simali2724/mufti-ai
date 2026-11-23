# Architecture

# At a glance — current architecture (updated 2026-11-17)

Read this section to understand the system as it is today. Everything after "HISTORY" records how
it got here, with the measurements behind each decision.

## Processes and dependencies
```
Browser (frontend/*.html|js|css, no build)  ──HTTP/SSE──►  FastAPI app :786 (app/main.py, uvicorn)
                                                              │
                     ┌────────────────────────────────────────┼─────────────────────────────┐
                     ▼                                        ▼                             ▼
          LangGraph pipeline (app/agents)          Ollama :11434 (local)          Cloud LLM APIs
          SQLite checkpointer                      bge-m3 embeddings (always)     Gemini (default),
          data/index/sessions.sqlite               qwen3:1.7b fallback answers    Anthropic, OpenAI
                     │
                     ▼
          data/index/: segments/<build> (Chroma + segments.json, active.json), chunks.json,
          pages-<book>.json, trees/<book>.json (outline), knowledge.sqlite (keyword graph),
          catalog.json · data/books/*.pdf · data/book-metadata/<book>.json (reviewed facts)
```

## Request lifecycle (`POST /chat`, explanation mode)
```
input ─► bibliography ──(reference question: "kis book se?")──────────────────────────► END (card, no model)
              │
              ▼
          language (reply language; rewrite follow-ups with history; Urdu/English variants)
              ▼
          router  ── greeting / unsafe / needs_topic / out_of_scope ──────────────► format
              ▼ (everything else is searched — no model may refuse before search)
          retrieve (hybrid search; optional chapter SCOPE with fallback) ─► evidence windows
              ▼
          explain (stream answer; STYLE note; FOCUS note; <<next:>> follow-ups; script guard;
                   strip markers; audit every sentence; renumber/validate citations)
              │── <<none>> and not yet expanded ─► expand (2nd search) ─► explain
              ▼
          format (outcome text, citations, related, follow-ups, history turn) ─► END
```
SSE events: `status` (task/provider/model progress), `draft` (live tokens), `draft_reset`
(provider switched mid-answer), `done` (the final checked `ChatResponse`), `error`.

## State contract (`app/agents/state.py`)
Per-turn inputs set in `graph._ask()`: `user_input`, `language_hint`, `answer_style`, `scope`,
plus reset values for `explanation`, `followups`, `answer_format`, `verification`, `errors`, rounds.
Produced: `detected_language`, `search_queries`, `matched_concepts` (language) → `intent` (router) →
`retrieved_chunks`, `evidence_windows`, `scope_applied` (retrieve) → `explanation`, `followups`,
`provider_used` (explain) → `final_answer`, `citations`, `related`, `coverage`, `reason_code`,
`history` (format). **Any per-turn key must be reset in `_ask()`** or the checkpoint leaks it.

## Model routing (`app/llm/router.py`)
Order from `model-settings.json` (UI): mode `auto|gemini|anthropic|openai|ollama` + cloud order;
Ollama always last. Within Gemini: selected model → `gemini_alternates`; per task `task_models`
(audit/language/router on lite models). 429 → model cooldown until `retryDelay`; timeout or stalled
stream (>60 s silence, `stream_read_timeout`) → next model; audit never on the local model.

## Grounding guarantees (where they are enforced)
| Guarantee | Enforced in |
|---|---|
| Model sees only readable book passages | `explain_agent.build_sources` + `evidence.legible_pieces` |
| Every citation refers to a supplied passage | `explain_agent.renumber` (invalid numbers dropped); no valid citation → `explanation_unverified` |
| Unsupported sentences corrected/removed | `explain_agent.audit` + `apply_fixes` (`plausible_fix` rejects meta "fixes") |
| Follow-ups are never facts | `suggest.clean` (no citations, length bounds); stripped before the audit |
| Styles never relax grounding | each `STYLE_NOTES` entry restates the citation rule; same audit |
| Scope never hides a refusal | fallback to the whole library, reported as `scope.applied=false` |

## Extension points
See ADD_FEATURE.md Part B for the full table. In short: request option → `schemas.py` +
`_ask()`; prompt change → `prompts.py` / `explain_agent.user_message`; same-call extra output →
hidden marker pattern (`suggest.split_followups`); new node → `graph.build_graph`; UI →
`frontend/*` with DOM-safe `element()`.

---

# HISTORY

Updated: 11 November 2026 (Asia/Kolkata).

## Runtime and boundaries
Local Windows application in D:\mufti-ai. FastAPI/Uvicorn serves the vanilla HTML/CSS/JavaScript frontend and API on 127.0.0.1:786. Ollama runs separately on port 11434. Cloud generation is optional; embeddings and default Whisper transcription remain local. No public deployment or authentication exists.

## Answer flow
POST /chat -> session lock -> immutable model preference snapshot -> LangGraph input -> language detection/query expansion -> intent -> hybrid retrieval -> relevance filtering -> answer -> verification -> formatter -> saved history.
Text requests use SSE status, token and done events. Only verified final answer text streams. Live status exposes agent task, actual provider/model and fallback failures, never credentials. Voice requests call the same ask() function after local transcription.

## Retrieval and evidence
PDFs under data/books are parsed/OCRed into page-bound chunks. Chroma supplies multilingual bge-m3 cosine search; BM25 and a lightweight SQLite keyword graph contribute rankings. Reciprocal rank fusion retains 3x retrieval_top_k candidates before relevance filtering selects retrieval_top_k. Alias expansion normalizes Mahomet/Mohammed to Muhammad and supplies an Urdu search variant. The answer agent sees three pages at a time and up to eight exact bounded quotes from each. If no direct answer is found, remaining retrieved candidates get one further batch. Every claim is bound to a real quote by code; the verifier checks exact support, language and relevance. Page IDs come from stored PDF metadata.

## Models
app/llm/preferences.py validates non-secret model-settings.json. Auto tries cloud_order then Ollama; preferred-cloud mode moves that provider first; Ollama-only skips clouds. Keys live in .env and only configured booleans reach the browser. Router skips missing keys/cooling clouds, retries transient failures twice, then falls through. Ollama is always attempted as the last option. Successful model calls populate request-local execution history; ContextVars isolate concurrent requests.

## Storage and ownership
data/index contains Chroma, OCR/embedding caches, catalogs and sessions.sqlite. ScopedSqliteSaver opens a fresh short-lived SQLite connection per operation (DELETE journaling, busy timeout, bounded retries), avoiding handles held during long generation. Preserve these databases and the original PDF. Never deploy a staging data directory over them. Runtime locks serialize Ollama model switching on limited GPU memory.

## Important modules
- app/main.py: lifespan, origin guard, routing and static files.
- app/agents/: pipeline, formatter and checkpoints.
- app/llm/: adapters, routing, preferences, structured schemas, progress events.
- app/retrieval/: dense/BM25/graph retrieval and reranking.
- app/ingestion/: PDF extraction, OCR, catalog and chunk metadata.
- app/api/: chat/SSE, voice, books, health, settings.
- frontend/: responsive emerald/ivory UI, dark mode and model dialog.
- tests/: deterministic offline checks; eval/: live evidence and evaluations.

## Constraints
Current book uses imperfect Urdu OCR. A small local model can miss an answer, mistranslate or fail verification. Cloud API access requires the user's keys and usable quota. Full-book answer coverage has not been established. Never convert retrieval similarity into a claim that an answer is verified.

## Reviewed bibliographic facts
Input first checks app/agents/bibliography.py. Narrow author/publisher/ISBN/title/first-publication questions can use visually reviewed facts stored in data/book-metadata/<book-id>.json, then finish with citations and saved history. Other questions continue through language, retrieval, generation and verification. Records require a review flag, matching indexed and current PDF SHA-256, a physical page and bounded original-script excerpt. Ambiguous book references and changed PDFs fall through. Citations carry transcription_reviewed; original OCR is preserved. These are direct book-fact lookups, not generated religious answers.

## Search quality repair (2026-11-11)
When the optional cross-encoder is disabled, retain reciprocal-rank fusion ordering after the relevance threshold; do not sort exclusively by dense similarity and discard the lexical signal. Quote selection prioritizes original question content words, using translated content words as a secondary signal and ignoring common stopwords. Model switching unloads only a model selected by this process; a missing previous model (404) is already unloaded. Service failures have a distinct localized answer and reason code.
## Coverage repair, 2026-11-12: what actually changed

### Two-layer index
The live page-level Chroma collection still exists and is never rebuilt by this path. Beside it,
`data/index/segments/<build-id>/` holds a staged **child-segment** build: paragraph-aware parent
units of roughly 900 characters, split into overlapping child windows of about 440 characters
with 110 characters of overlap. Search runs over the children; answering fetches the whole parent
plus a neighbour when the parent is short. A build becomes live only when `activate` writes
`active.json`, and `rollback` reverses it. A build records its embedding model and is refused if
the configured model no longer matches, because changing the embedding model invalidates every
vector. Active build: `20261112-094445`, 3338 segments over 661 pages, `bge-m3`.

Each segment keeps the physical PDF page and the printed page label as separate fields, plus raw
OCR versus reviewed correction and the correction provenance. `validate` enforces that every
child is a contiguous run of its parent (whitespace-normalised) and that every readable page
produced at least one segment; it reports all offenders rather than stopping at the first.

A page's embedded English layer is split into its own blocks, so a page whose Urdu OCR is
garbled can still be found and quoted through clean English prose. 634 of 689 pages have such a
layer; the extraction audit in `data/index/extraction-audit.json` scores all 689 and flags 181.

### Retrieval
Multi-query hybrid search: the original question, **its content words**, reviewed lexicon
variants across scripts, then adjacent related concepts, each run through BM25 and dense bge-m3
and fused by reciprocal rank. Per-retriever scores survive fusion so a strong exact-word hit is
not vetoed by dense similarity. The BM25 tokenised index is cached and keyed by corpus content,
because it was being rebuilt over all 3338 segments once per query variant.

The content-word variant exists because a long natural question dilutes BM25: its few
high-information words are outvoted by the many low-information ones. It is derived only from the
user's own wording, carries the origin tag `content_words`, and adds a query without removing
anything.

The model query-rewrite now runs only when there is conversation context to resolve or a cloud
model is available. Measured, it changed no retrieval outcome locally while costing 90-144s per
question in GPU model swapping.

### Evidence and answering
`app/retrieval/evidence.py` builds whole-parent-paragraph windows, numbered into verbatim spans.
The model cites span ids and code resolves them back to exact source text, so a display quote can
be short while the verified support stays whole. Evidence size is fitted to the model that will
actually answer: 6 windows / 1500 tokens locally, 8 / 7000 for a cloud model. The passage is sent
once, as its numbered spans — sending both the passage and its spans doubled the real context.

### Fitting the work to a 2 GB GPU
This machine has an NVIDIA MX450 with 2 GB. Local generation runs at 1.6-3.0 tokens/s, so output
length is the dominant cost and these are latency decisions, not style ones:
- The JSON schema sent to a local model has its length and count bounds stripped
  (`structured.relax_for_grammar`), because llama.cpp expands `maxLength` into GBNF repetition:
  identical output took 394s with the bounds and 215s without. The bounds are enforced in code
  in `answer_agent.attach_support` instead. Removing the schema altogether yields unusable output.
- `provider_timeout` is per provider: 180s for cloud, `ollama_timeout` 900s for local, because a
  legitimate local answer call takes minutes and was previously killed at 180s and reported to
  the reader as "no answering model could be reached".
- A second search round is taken only when the answering model is a cloud one
  (`max_search_rounds_local`). Locally the second answer call was observed timing out twice,
  taking the request past 1800s until the client gave up.
- Claims are verified in batches sized to the verifier schema's claim-id range, so a long
  sectioned answer does not lose its later claims.

### Verification
Per claim, a code-checkable pass first, then one model verdict per claim covering entailment,
attribution and whether it answers the question. The code pass now also enforces two rules that
do not depend on model judgement:
- **Concept guard**: when the question matched a reviewed lexicon concept, the span a claim rests
  on must carry one of that concept's surface forms in some script. This stops a gender-equality
  question being answered from a page about constitutional equality between the Charter's parties.
- **Attribution guard**: a window that credits an outside writer in the book's own
  "Surname, Title, p. N" form requires any claim drawn from it to name that writer, so a quoted
  view does not become the book's own conclusion. `evidence_payload` tells the model which
  writers a passage quotes so it can comply.
A missing final full stop is repaired rather than used to reject a supported claim; a claim that
trails off in a connector is still rejected.

### Known limits of this design on this hardware
A 1.7B-3B local model drafts claims that fail honest verification: it copies spans verbatim,
transfers a quoted opinion to the book, and asserts propositions its Urdu span does not make.
The guards above catch specific cases, but cross-lingual entailment from garbled Urdu OCR is not
reliably checkable in code and the local verifier is as weak as the drafter. On this hardware the
app therefore refuses more often than it answers, and that refusal is the correct outcome. Do not
convert retrieval similarity, or a same-model approval, into a claim that an answer is verified.

## Answer-quality repair, 2026-11-13: drafting, verification and the page tree

The previous checkpoint concluded that retrieval was fixed and that a 1.7B-3B local model
simply "cannot draft a properly attributed, concept-correct claim that survives honest
verification". Re-measuring showed that conclusion was premature: three separate defects in
the drafting and verification stages were producing refusals that no model could have
avoided, and the gender-equality question now answers.

### A claim is repaired before it is abandoned

`app/agents/repair_agent.py` is a new bounded graph node between `verify` and `expand`. The
brief requires a specific rejected claim to be repaired from its own evidence and feedback
first; before this, the only recovery route was `expand`, which re-searches the whole book and
redrafts the entire answer. That is the wrong tool for the failure actually measured here,
where retrieval and evidence were already correct and one sentence was defective.

Two routes, cheapest first:

1. **Deterministic attribution.** When a claim drawn from a quoted passage does not name the
   writer the book credits, the code already knows the names from the book's own citation
   line and writes them in. No model call, so 0 s against 60-300 s locally. It adds
   attribution, never support: the repaired sentence is verified again afterwards.
2. **Model redraft** of the remaining repairable defects, given the claim, its verbatim span
   and the exact rejection reason. The evidence is fixed; only the wording may change.

A claim resting on the wrong concept's span, citing nothing, or citing a span that does not
exist is NOT repairable: there is nothing in its evidence to rewrite, and finding it a
different source is the fabrication the guards exist to stop. Verified claims are carried
through a repair round without being re-judged, so nothing that already worked is paid for
twice or lost to a small model contradicting itself.

### Guards made scoped, and new guards added

Every guard below is code-checkable and tested in both directions in
`tests/test_answer_quality.py`: each relaxation has a negative case proving the protection it
loosened still holds, and each new rejection has a positive case proving it does not refuse a
sound claim.

| Guard | Change | Why |
|---|---|---|
| Attribution | window-wide to span-scoped, by citation position | The brief: attribution attaches to the quoted span, not to every sentence in a paragraph carrying a footnote. Measured: releases 4.1% of spans in 21 of the 124 parents that cite an outside writer; page 50 is still fully covered. |
| Concept | span keyword required, then span / rival-concept veto / parent paragraph | A faithful paraphrase of the next sentence of the same quoted paragraph does not repeat the keyword. The page-280 constitutional-equality rejection still holds. |
| Relevance (`answers_question`) | hard gate to gating only questions that demand a relation | The local verifier returned `answers_question=false` while its own feedback read "The claim is fully entailed by the span." A self-contradicting verdict must not manufacture a refusal. Claims kept this way are marked advisory and force `coverage: partial`. |
| Grounding floor | NEW | A same-language claim must reuse at least 40% of its content words from its span and must not invent 8 or more words the span never uses. Catches the measured fabrication "Gender equality is a fundamental principle in Islam..." that the 1.7B verifier approved. Never applied across scripts, where a faithful translation shares no tokens. |
| Copied span | NEW | The reader asked for an explanation, not pasted quotations. Once the qualification guard landed, reproducing the sentence verbatim was the cheapest way to satisfy it. |
| Dropped qualification | NEW | The span says gender equality "could plausibly" lie at the heart of a clash; the model restated it as settled fact. Scoped to the one sentence the claim restates, so an unrelated hedge elsewhere does not refuse it. |
| One sentence | NEW | Asked to repair a fabricated claim, the model kept the fabrication and GLUED a correct attributed sentence onto it. Every guard passed individually while the claim still fabricated. |
| Bibliography-only | NEW | A citation line matches the question's words and states nothing a claim can rest on. |

### Book, Chapter, Section, physical page-range tree

`app/ingestion/book_tree.py` builds a persistent tree from the PDF's own outline, which
nothing in the application was using. For this book: 310 outline entries give 9 chapters and
301 sections, 0 validation problems, with stable IDs, parent links, validated page ranges and
the source PDF hash. No model is called.

Its titles are the point. The body text is OCR over legacy InPage fonts and is degraded; the
outline is embedded text and is correctly spelled. PDF page 280's body reads
"آینی مساوات کا جق"; its outline title reads "آئینی مساوات کا حق". The tree therefore supplies
two things the OCR cannot:

- **Clean evidence headings.** The old `chapter` field held whatever text topped the page,
  including running headers and, on one page, the publisher's street address.
- **Rival-concept detection.** Page 280 is recognised as *constitutional* equality by name,
  which the garbled body text never matched.

A heading locates a section and is never evidence for its substantive claims, so the tree
contributes candidate pages only and answers are still drafted from the real paragraphs.

### Concept classification is three-way, on measurement

Two benchmark cases pulled in opposite directions. On gender equality the passages crowding
the budget carried a *different reviewed concept* and the drafter wrote six rejected claims
from them. On `west-en-2` the passages being held back carried no reviewed concept wording at
all, only because the lexicon has no entry for their subject, and demoting them lost the
case. So only a passage carrying a RIVAL reviewed concept is demoted and capped; a passage
the lexicon says nothing about is left alone. Absence from a hand-written lexicon is not
evidence that a passage is off topic. The adjacent-concept cap is also soft: it stops rival
material crowding out better evidence, and never leaves the model with less evidence than was
available.

### PageIndex: evaluated, not integrated

The official project (github.com/VectifyAI/PageIndex, PyPI `pageindex` 0.5.3, MIT, read
2026-11-13) was assessed against this deployment and **not adopted**, for reasons that are
properties of this machine and this book rather than of the package:

- Its local mode still requires an LLM provider key for indexing *and* calls a chat model on
  every query. On this 2 GB MX450 one local model call is 60-300 s, so a per-query tree search
  is not affordable, and there is no paid cloud quota to rely on.
- Local indexing reads the PDF's **text layer** and runs no OCR. This book's text layer is the
  degraded InPage output, which is exactly the input the tree is meant to avoid.
- Urdu, Arabic and right-to-left handling are undocumented; the published benchmarks are
  English 10-K and academic documents.

What this book actually needed from that idea, a validated chapter/section/page-range tree, is
available for free from the PDF outline with no model calls. `app/ingestion/book_tree.py` is
therefore labelled **PageIndex-inspired**, not the official integration, as the brief
requires. `app/retrieval/tree_nav.py` implements the bounded navigation route; it is
**disabled by default on measurement** (see `enable_tree_route` in `app/core/config.py`):
over all 48 cases it left window_recall and top3_recall identical and lowered candidate_recall
from 0.881 to 0.857. The tree's metadata contribution is used regardless of that flag.

## Explanation mode, 2026-11-16: the default answer path

The user's requirement: any question about the book gets a complete, respectful, well-organised
answer, the way a chat assistant explains — and no refusal when the book carries the answer.
The claim pipeline could not meet it (≤ 8 one-sentence claims; any claim a verifier doubted was
dropped, often down to a refusal). The graph now branches after retrieval:

```
retrieve ──► explain ──► format                      (answer_mode = 'explain', default)
   │            └─(<<none>>, first round)─► expand ─► explain
   └──────► answer ─► verify ─► repair/expand ─► format   (answer_mode = 'strict')
```

| Piece | File | What it does |
|---|---|---|
| Sources | `explain_agent.build_sources` | Evidence windows → numbered sources of **readable spans only**, with section title, outside-writer and adjacent-topic notes |
| Generation | `explain_agent.run`, `prompts.EXPLAIN_RULES` | One streamed Markdown answer: hidden `<<full>>/<<partial>>/<<none>>` marker, direct answer, `###` sections, bullets, summary, `[n]` after every factual sentence, adab, reply language |
| Streaming | `providers.stream_complete`, `router.ChatModel.stream`, `progress.draft_token` | Gemini SSE, Ollama NDJSON, OpenAI/Anthropic SSE → `event: draft` to the browser; `draft_reset` if a provider fails mid-answer |
| Citation check | `explain_agent.renumber` | Citations to sources that were not supplied are dropped; display numbers 1..k by first use; no valid citation → `explanation_unverified` |
| Audit | `explain_agent.audit`, `prompts.AUDIT_RULES`, schema `audit` | One JSON call over ALL sources + numbered sentences; returns only problem sentences (`unsupported / contradicted / misattributed / overstated`) with a minimal fix or `""`. Fixes are applied in place by position; implausible fixes (repeated, meta "supported by sources", much longer) are ignored |
| Provider routing | `router._route` | Selected model → `<provider>_alternates` on 404/429/503 → next provider. The audit task is never routed to the local model (`audit_local = False`) |
| Output | `formatter.run` | `answer_format='markdown'`, `verification='audited' \| 'citations_checked'`, citations with best-matching excerpt and full source text |
| UI | `frontend/app.js` | Safe Markdown renderer (text nodes only), `[n]` chips open the page dialog, live drafting cursor, verification badge, copy button |

Evidence budget for cloud models rose from 8 windows / 7 000 tokens to 12 / 12 000; local stays
6 / 1 500 (measured on the 2 GB GPU). Cost per question on Gemini: one generation call, one audit
call, plus a query-rewrite call only when there is conversation history or no lexicon concept
matched.
