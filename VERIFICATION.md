# Local verification

Application: http://localhost:786

- Source and environment: `D:\mufti-ai`.
- Ollama chat: `qwen3:1.7b`; multilingual embeddings: `bge-m3`.
- Unit/integration suite: **29 passed**. The Windows PDF fixture also passed using isolated worker processes.
- Library: **689 PDF pages processed; 662 passages indexed**.
- Low-readable-text pages: **28**. These pages did not produce usable passages and remain available in the original PDF.
- Local voice: generated Hello recording returned HTTP 200, transcript Hello and the expected greeting.
- Conversation history: saving, reading and wiping verified with a synthetic session.
- Checkpoint I/O uses a fresh connection for each short operation, rollback journaling and bounded retries; no connection is held during model generation.
- MCP stdio: registration of four tools and books://catalog verified; the list_books call succeeded.
- Server bound to 127.0.0.1 on port 786; this is local hosting.

## Live questions

| Language | Question | Result | PDF pages | Seconds |
| --- | --- | --- | --- | --- |
| English | What does the book say about personal piety and worship of God? | Answer with checked source quotes | 51 | 165.1 |
| Hindi | इस किताब में सीरत के अध्ययन का क्या महत्व बताया गया है? | No verified answer; safe refusal | — | 309.9 |
| Urdu | اس کتاب میں سیرت کے مطالعے کی اہمیت کیا بیان کی گئی ہے؟ | No verified answer; safe refusal | — | 225.5 |
| English | How do I repair a spaceship engine? | No verified answer; safe refusal | — | 45.6 |

Detailed responses: [eval/live-self-check.json](eval/live-self-check.json).

## OCR review

Pages requiring review: 1, 25, 30, 31, 73, 74, 75, 108, 109, 182, 183, 245, 246, 247, 382, 386, 387, 472, 473, 543, 544, 545, 563, 595, 618, 619, 641, 659.

Urdu Nastaliq OCR remains imperfect, including on pages that yielded text. The application checks source quotations, sentence completeness, answer relevance and language, but this is not a guarantee of factual or religious correctness. Important wording should be checked in the original PDF.

Local generation can take several minutes on this 2 GB GPU. Optional cloud providers, Docker, the optional cross-encoder and HTTP MCP transport were not exercised in this installation.

The most recent ingestion report can describe an incremental run that skipped unchanged books; the catalog above records the full library totals.

## Provider selection update — 11 November 2026

- Auto/preferred-cloud/Ollama-only modes implemented. Auto tries Anthropic, OpenAI, Gemini, then the selected installed Ollama chat model. Missing keys are skipped.
- Model IDs and priorities persist without secrets; each complete question uses an isolated settings snapshot.
- Provider settings and adapter checks: 53 passed in the installed D: project. Earlier full workspace suite: 58 passed; the two new API/adapter test files add 19 passing cases (77 distinct cases in total).
- Cloud 429 exhaustion, timeouts, invalid credentials/model IDs, local circuit recovery, secret rejection, model discovery and concurrent preference isolation tested offline with mocked providers.
- Real local Gemma 3 1B returned HTTP 200 and valid structured output through Auto fallback. Gemma is installed alongside Qwen.
- Browser checked model dropdowns, automatic unique-priority swapping, saving Auto preferences, and saved settings retrieval.
- Current clouds have no keys configured. No real cloud API generation or real account quota exhaustion was exercised.
- Library remains complete: 689 PDF pages, 662 indexed passages, 28 review pages. Storage health: ok. Server: http://localhost:786.
- Daily run and key setup commands: RUN_COMMANDS.md.

## Model visibility and retrieval improvement
81 offline tests passed. Live results: eval/improvement-live.json. Both screenshot question and known book question produced grounded citations (pages 201/234 and 51 respectively). Browser verified selected model, live actual model changes, actual Gemini 429 fallback to Ollama, and persisted source/model metadata after reload. UTF-8 display repaired and verified. See Handsover.md for stopping point and remaining quality/latency work.

## Bibliographic answer correction
Visually inspected PDF pages 2/3. Corrupt author OCR was isolated from reviewed title-page facts. Six live API cases passed: author English/Urdu/Hindi, publisher, ISBN and first publication; results in eval/bibliography-live.json. Full suite 98 passed, then focused language/bibliography 23 passed after adding one regression (99 distinct cases). Ordinary generated-answer verification remains unchanged. Browser observed the exact user question answered with page 3.


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
## Coverage repair verification — 2026-11-12

Everything below was observed. Anything not observed is listed under "Not verified" and must
not be reported as working.

### Offline checks
- `.\.venv\Scripts\python.exe -m pytest tests -q` -> **133 passed**.
- `node --check frontend/app.js` -> passed.
- New regressions, each written against a failure actually reproduced this session:
  - `test_long_answer_claims_are_all_verified_in_batches` — claims past the verifier schema's
    claim-id range used to get no verdict and be rejected as unsupported.
  - `test_expand_round_records_diagnostics_without_crashing` — the second search round raised
    `TypeError: got multiple values for keyword argument 'queries'` and killed the request.
  - `test_expand_round_keeps_the_first_rounds_evidence` — the second round replaced the first
    round's windows, discarding the page that answered the question.
  - `test_local_models_report_the_first_round_instead_of_a_second_expensive_one` and
    `test_max_search_rounds_follows_the_answering_provider`.
  - `test_a_claim_is_not_discarded_for_a_missing_full_stop`.
  - `test_claim_from_an_adjacent_concepts_span_is_not_accepted_as_support` — built from the real
    page-280 Urdu span that produced three approved fabrications.
  - `test_a_quoted_outside_writer_keeps_their_attribution` — built from the real page-50 text
    carrying the Inglehart/Norris citation.
  - `test_evidence_payload_sends_each_passage_once`.
  - `test_bm25_index_cache_does_not_serve_a_stale_corpus`.
  - `test_rewrite_is_skipped_on_a_local_model_but_kept_for_conversation_context`.

### Index verification
```
.\.venv\Scripts\python.exe -m app.ingestion.segment_index status
```
Active build `20261112-094445`, 3338 segments, 661 pages, `bge-m3`. `validate` returns
`ok: true` with no issues, including the child-in-parent containment check over all 3338
segments and the "every readable page produced a segment" check. Verified separately that no
parent loses a word to chunking (1541 parents, 0 with missing words). The live page index was
not rebuilt or overwritten.

### Retrieval measurement — 48 cases, 42 answerable
| | OLD pipeline replayed | current |
|---|---|---|
| candidate_recall | 0.810 | **0.881** |
| reviewed page reaches the answering model | **0.643** | **0.810** |
| misses at the answer stage | 15 | **8** |

Artefacts: `eval/benchmark-baseline.json`, `eval/benchmark-retrieval-content.json`,
`eval/benchmark-retrieval-segments-norewrite.json`,
`eval/benchmark-retrieval-segments-rewrite-on-partial.json`.

Of the 8 misses, 3 are bibliographic questions answered by `bibliography.py` before retrieval
runs (harness artefact), and 3 (`seerah-en-1/ur-1/hg-1`) expect table-of-contents pages that
carry topic words but no supporting prose — a benchmark ground-truth error to re-review, not a
retrieval target. Genuinely unexplained: `cm-hi-1`, `cm-en-6`.

The model query-rewrite was measured on the 29 cases that ran both ways: identical window and
top-3 recall, total time 1102 s -> 106 s. Removed for local models on that evidence.

### Live service verification
- App serving `http://localhost:786`, started hidden with uvicorn. Launch pid 5824, **actual
  listener pid 15732** — always identify the listener rather than trusting a recorded pid.
- `GET /health` -> `status: ok`, `embedding_model: bge-m3`, `chat_model: qwen3:1.7b`.
- `GET /settings/models` -> `mode=ollama`, `ollama=qwen3:1.7b`, `local_online=True`,
  installed `gemma3:1b, llama3.2:3b, qwen3:1.7b`. Provider labels are honest, not a blanket
  Ready: `anthropic No API key`, `openai No API key`, `gemini Key configured · not yet used`,
  `ollama Ollama running`.
- `POST /chat` with the author question -> 1 s, `grounded: true`, PDF page 3,
  Dr. Muhammad Tahir-ul-Qadri, via the reviewed bibliography path with no model generation.
- `POST /chat` with `Explain Gender Equality in detail` -> **66.3 s**,
  `reason_code: unsupported_claims`, evidence pages `[50, 257, 282, 286, 14, 280]`, related
  pages `[50, 257, 282]`. Saved: `eval/ge-live-http.json`.
- **Gemini quota: a direct call returned a real HTTP 429.** Not simulated. So every local
  fallback observed this session was real, and no cloud generation could be exercised.

### Manual quality review of the gender-equality answer — FAILED
Reviewed against the original PDF pages 50 and 257. The intermediate output that reported
`grounded: true, coverage: partial` was **wrong**: three claims rested on page 280, which is
about *constitutional* equality among the Charter of Madinah's parties, and asserted statements
about the Quran and about "both genders" that the span does not make; the page-50 claim dropped
the Inglehart/Norris attribution and presented their quoted view as the book's own conclusion;
and a page-257 claim welded "Conditional Superordination of State" to gender equality.

A 1.7B verifier approved a 1.7B drafter's fabrications. Same failure class as
`eval/rejected-book-quality-example.json`, which remains a rejected example and never a metric.

After adding the concept guard and the attribution guard, the same question returns
`unsupported_claims` and shows pages 50, 257 and 282 as related material. All 8 drafted claims
were rejected by the code guards alone: 2 for missing attribution, 6 for resting on an adjacent
concept's span. That refusal is correct, and it is still not the scoped answer the brief wanted.
`tests/test_evidence_ranking.py` demonstrates that a correctly attributed claim on the same
page-50 text passes both guards, so the pipeline is right and the local model is the limit.

### Not verified — do not report these as working
- **No `--answers` benchmark pass.** 4.5-7 hours at 340-550 s per case. There is therefore NO
  measured `answered_rate`, `false_refusal_rate`, `answered_absent_topic_rate`,
  `citation_page_accuracy` or `citations_verbatim_rate`. No such number exists; do not quote one.
- **No browser check and no screenshot this session.** The UI was never opened. The earlier
  `answer-verification.jpg` and `author-verification.jpg` are from previous sessions and do not
  show any of today's changes.
- The false-refusal cost of the concept and attribution guards is unmeasured across the
  benchmark. The attribution guard is deliberately conservative: it demands attribution for
  every claim from a window that credits an outside writer anywhere in it.
- No cloud generation of any kind was exercised (quota exhausted).
- Voice input/output was not touched or retested.


---

# Verification — 2026-11-13 answer-stage repair

Everything below was measured on this machine on 2026-11-13. Where a number is missing it is
said to be missing; no figure here is estimated or carried over from an earlier session.

**Configuration.** Segment build `20261112-094445`, 3,338 segments over 661 pages, embeddings
`bge-m3`. Local generation `qwen3:1.7b` via Ollama on an NVIDIA MX450 with 2 GB VRAM. Cloud
generation `gemini-2.5-flash`. Evidence windows 6 locally (`evidence_windows`), page-tree
route off by default (`enable_tree_route=False`), `off_concept_factor=0.9`.

## Test suite

**167 passed**, offline, no model calls. `node --check frontend/app.js` passes.

41 of those are new this session: 27 in `tests/test_answer_quality.py` and 9 in
`tests/test_book_tree.py`. Each one was written from a failure that actually occurred, and each
guard is tested in both directions — every relaxation has a negative case proving the
protection it loosened still holds, and every new rejection has a positive case proving it does
not refuse a sound claim. Tests write diagnostics to a temporary directory, never into
`data/diagnostics/`, so mocked runs cannot be mistaken for live evidence.

## Retrieval, all 48 benchmark cases (42 answerable)

Measured with `eval.run_benchmark --retrieval --holdout`. Candidate recall is whether a
reviewed page reaches the candidate pool; window recall is whether it reaches the answering
model; top-3 is whether it is among the first three windows.

| Configuration | candidate_recall | window_recall | top3_recall | median s |
|---|---|---|---|---|
| Previous session's best (8 windows) | 0.881 | 0.810 | 0.738 | — |
| **Shipping: hybrid, tree off, factor 0.9** | **0.881** | **0.810** | **0.738** | **2.42** |
| Hybrid + page-tree route | 0.857 | 0.810 | 0.738 | 2.53 |

**The page-tree route is off by default because it did not improve measured quality.** It left
both recall figures identical, lowered candidate recall by spending the candidate budget, and
cost about 0.1 s per question. The brief asks for the simplest configuration that improves
measured quality; this is not one. The tree's *metadata* contribution is used regardless of the
flag and is genuinely valuable (clean headings, rival-concept detection).

### Two regressions I introduced, found by measurement and fixed

Neither would have been visible without re-running the benchmark.

1. **A hard adjacent-concept cap cut evidence instead of reordering it.** On `west-en-2` it
   reduced the evidence from eight windows to three and lost the reviewed pages. The cap is now
   soft: a second pass restores held-back passages once nothing better competes for the budget.
   window_recall 0.762 to 0.786.
2. **Demoting everything the lexicon did not recognise was wrong.** `off_concept_factor` swept
   against the full benchmark:

   | factor | window_recall | top3_recall |
   |---|---|---|
   | 0.55 | 0.786 | 0.690 |
   | 0.75 | 0.810 | 0.714 |
   | **0.90** | **0.810** | **0.738** |
   | 1.00 (no demotion) | 0.810 | 0.738 |

   0.9 shipped: it orders on-concept material first at **zero measured retrieval cost**.
   Classification is now three-way, so only a passage carrying a *rival reviewed concept* is
   demoted; a passage the lexicon says nothing about is left alone.

### Retrieval misses, unchanged from the previous session

`author-en-1`, `author-ur-1`, `pub-en-1` are bibliographic questions answered by
`app/agents/bibliography.py` *before* retrieval runs, so they are not failures of the live
app — the retrieval-only harness bypasses that agent. `cm-hi-1` and `cm-en-6` remain
unexplained. `seerah-en-1/ur-1/hg-1` expect contents and heading pages (page 17's entire English
layer is `i ii iii iv v i ii iii`); those expectations need re-reviewing against the book's
actual prose before their contribution means anything. **Do not tune retrieval to satisfy them.**

## The gender-equality question

The acceptance case. Reproduced many times; the runs below are real, with traces in
`data/diagnostics/`.

### With a capable model (gemini-2.5-flash), 47 s

> **Gender Equality as a Cultural Difference**
> Ronald Inglehart and Pippa Norris state that gender equality and sexual liberalization are
> fundamental cultural differences between the West and Islam. [1]
> According to Inglehart and Norris, these social values could plausibly be central to any
> conflict between Islam and the West. [1]
> Inglehart and Norris's analysis reveals a more significant gap between Islam and the West on
> these issues than on political values. [1]
>
> **Principles of Equality**
> There is a principle of no gender discrimination in adult franchise. [2]
>
> **Not covered in this book** · A detailed explanation of what gender equality entails in an
> Islamic context · Specific examples or practical applications · How gender equality is
> implemented in Islamic law or society
>
> [1] PDF page 50 (printed 49) · [2] PDF page 257 (printed 16)

Checked by hand against the PDF: attribution to Inglehart and Norris preserved on every claim
drawn from the quoted block; the source's hedge "could plausibly" preserved; the page-257 claim
**scoped to adult franchise** rather than inflated into a general position on gender equality;
citations are exactly the two pages the brief names. Saved: `eval/ge-gemini.json`.

### On the local 1.7B model

Two honest outcomes, depending on what the drafter produces:

- `grounded: true, coverage: partial`, one or two correctly attributed claims from page 50,
  e.g. *"As quoted from Ronald Inglehart and Pippa Norris: the analysis of these social
  attitudes reveals a significant gap between Islamic and Western values, particularly in
  gender equality."* 134-148 s. Saved: `eval/ge-final.json`.
- `reason_code: explanation_unverified` — the new outcome — showing the book's own excerpts
  with working page links, clearly labelled *"These are source excerpts, not an explanation."*
  420 s through the server. Saved: `eval/ge-live-http.json`.

**Neither says the book has no answer.** That was the previous behaviour and it was wrong: the
material is printed on pages 50 and 257.

### What each change contributed, measured on this question

| State | Result |
|---|---|
| Session start | `unsupported_claims`; 8 claims drafted, all 8 rejected; reader told the book does not answer |
| + span-scoped attribution + targeted repair | 3 claims repaired deterministically, 0 verified — verifier rejected its own entailed claims |
| + relevance verdict scoped | **grounded, 1 claim**, correctly attributed |
| + concept-aware evidence | evidence 1,349 to 733 tokens; 4 garbled off-concept windows to 2; page 257's gender clause citable on its own |
| + grounding floor, one-sentence, hedge, copy guards | fabrications and pasted quotes refused; the answer is a paraphrase that keeps the hedge |

### A fabrication this session caught — and nearly shipped

Loosening one verifier instruction to reduce false refusals immediately produced, and
**approved**, this claim from page 50:

> "Gender equality is a fundamental principle in Islam, emphasizing the equal rights and
> responsibilities of men and women in all aspects of life."

The span calls gender equality a point of **difference** between Islam and the West and says
nothing about rights, responsibilities, or what Islam holds. It is a plausible-sounding
religious statement the book never makes — the worst failure this application can have. The
verifier prompt now carries that exact case as a worked negative example, and
`verifier_agent.weakly_grounded` catches it in code without relying on the model's judgement.
A second attempt by the repair model to rescue it by **gluing a correct attributed sentence onto
the fabricated one** is caught by the one-sentence rule.

## Attribution guard, measured over the whole corpus

Of 1,541 parent paragraphs, **124 (8.0%)** credit an outside writer, containing 799 spans. The
old window-wide guard demanded attribution for all 799. The span-scoped guard demands it for
**766**, releasing 33 spans across 21 paragraphs — material printed after the citation that
closes a quotation, which is the book speaking in its own voice. Page 50 remains fully covered,
so the protection that matters is unchanged.

## Answer stage — partial, and honestly incomplete

**No complete answer-stage benchmark exists yet, and none ever has for this project.** Do not
quote an `answered_rate` or `false_refusal_rate` from any document: none is measured over the
full 48 cases.

**Cloud attempt, 3 of 48 cases, then blocked by quota.** `gemini-2.5-flash` answered live
(the previous session's permanent HTTP 429 was a quota window, not a dead key), but the free
tier rate-limits far below the speed the harness asks questions. A 429 trips the circuit
breaker and silently falls the request through to the local model, which makes the run measure
two providers at once. The harness now has `--delay` for this, but the daily quota was
exhausted before a full pass could run. Partial results, `eval/benchmark-answers-gemini-partial.json`:

| case | expectation | grounded | cited | expected | citation hit | verbatim | s |
|---|---|---|---|---|---|---|---|
| ge-en-1 | answerable_partial | yes | 257 | 50, 257 | yes | yes | 102 |
| ge-en-2 | answerable_partial | yes | 257, 50 | 50, 257, 286 | yes | yes | 78 |
| ge-ur-1 | answerable_partial | **no** | — | 50, 257 | — | — | 124 |

`ge-ur-1` is a **false refusal** and the known hard case: the question asks in correct Urdu
(`صنفی مساوات`) while the book's page-50 wording is `نوعی مساوات`. The lexicon carries both, and
retrieval finds the page; the failure is at the answer stage. This is the first time it has
been measured, and it is the most valuable single lead for the next session.

**Local full pass is running** against `qwen3:1.7b`, resumable, writing
`eval/benchmark-answers-local.json` after every case. At 2-7 minutes per case it is several
hours. Resume it with the command in RUN_COMMANDS.md; do not start it from scratch.

## Live verification through the running server

Server started from `D:\mufti-ai` on `http://127.0.0.1:786`.

| Check | Result |
|---|---|
| `GET /health` | `status: ok`, storage ok, 1 book, `bge-m3` / `qwen3:1.7b` |
| `GET /` and assets | HTML served; `/style.css` and `/app.js` both HTTP 200 |
| `GET /settings/models` | Reports gemini `"Key configured · not yet used"` with *"A configured key does not guarantee available quota"*, and Ollama `"Ollama running"` — selected vs actual provider kept distinct |
| `GET /books` | 689 pages, 662 passages, 28 pages flagged for review |
| `GET /books/{id}/pages/50` | Urdu layer, embedded English layer, `printed_label: 49`, extraction quality 1.0 |
| `GET /books/{id}/pdf` | HTTP 200, `application/pdf`, 16,770,999 bytes, `accept-ranges: bytes` so page links can jump |
| `POST /chat` (live, saved Ollama settings) | HTTP 200 in 420 s, `explanation_unverified`, excerpts from pages 50 and 257 with correct spans |

**A browser check with the Chrome extension was not possible** — the extension was not
connected this session. The UI was verified at the HTTP layer the browser uses, and the new
reason codes were confirmed present in `frontend/app.js`. A visual check is still outstanding.

## MCP integration

`mcp_server/server.py`: `search_books` **was broken and is fixed** — it called
`search_local(query, top_k=…)`, but that function takes `(queries, limit)` and expects a list
of query descriptors, so every invocation raised `TypeError`. It now goes through
`hybrid.search`. Added `list_sections`, `get_section` and `locate_page` over the new tree, as
the brief requires, each validating its ids against the catalogue and bounding what it returns.
Verified directly: section `s7` resolves to "اِسلام اور مغرب کی معاشرتی اَقدار کا فرق" on page
50; unknown book and section ids return errors rather than guesses.

## Caching, audited

| Cache | Key | Invalidation |
|---|---|---|
| Query embeddings | `sha256(embedding_model + text)`, LRU 128 | Model change changes the key |
| Indexed embeddings | same, on disk | Model change changes the key |
| BM25 index | corpus size + hash of every id | Re-index or build switch |
| Segment corpus | `build_id` | Activating a different build |
| Book tree | `book_id`, dropped on rebuild; **stale tree detected** by comparing the recorded PDF SHA-256 against the catalogue's | Replaced PDF |

**There is no response cache**, so the brief's "never reuse a superficially similar answer when
the question's conditions differ" cannot be violated. Provider-side prompt/context caching was
**not** implemented: the primary path is a local model where it does not apply, and there is no
cloud quota against which a benefit could be measured. Ordinary response caching and model
context caching are not the same thing and neither is claimed here.

## Hardware and environment, re-measured

- GPU: NVIDIA GeForce MX450, 2 GB. Local generation remains the binding constraint: an answer
  call is 60-300 s and a full request 130-420 s.
- Gemini quota resets. Re-check before recording a provider as unavailable.
- **D: is an external SSD that disconnected repeatedly.** At worst, 6,653 Windows disk I/O
  errors in 20 minutes; the source PDF and every `.md` became unreadable and the server was
  killed mid-request by `OSError: [Errno 22] Invalid argument: '.env'`. `Get-ChildItem` lists
  files whose contents cannot be read, so a directory listing proves nothing. A complete
  working backup is at `C:\mufti-ai-salvage` and the suite passes from it unchanged.
- Ollama wedged once after hours of heavy work: a request hung for 12 minutes with the server
  idle and no model loaded. Restarting `ollama serve` cleared it.

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

## Explanation mode verification — 2026-11-16

| Check | Result | Artefact |
|---|---|---|
| Offline suite | **205 passed** (19 new in `tests/test_explain.py`) | `pytest tests -q` |
| UI syntax / renderer | `node --check` OK; headless DOM test: headings, lists, chips render; `<img onerror>` stays text | session check |
| Full live benchmark (48 cases, Gemini route, mixed flash/flash-lite as quotas ran out) | answered 41/42 answerable (0.976); false refusal comp-en-4; page-hit 0.854; absent answered 2/6 (both said "not in book"); median 23.5 s; 39 audited | `eval/explain-eval-gemini.json` |
| Targeted rerun after fixes (10 cases, gemini-3.5-flash-lite) | 6/6 answerable answered, page-hit 0.833; 0/4 absent answered; median 13.5 s | `eval/explain-eval-rerun.json` |
| Gender equality, English (gemini-2.5-flash) | audited answer, Inglehart/Norris attribution and "could plausibly" hedge kept, pages 50/257/286; 29 s | `eval/explain-ge-en.json` |
| Live HTTP stream, Hinglish Hijrat question | 44 `draft` events, audited, 8 citations, 20.8 s | server on :786 |
| Follow-up in same session | context used, audited, 40 s; history reload keeps Markdown + citations | `/sessions/livecheck1` |
| Gemini quota | 2.5-flash and 3.5-flash: 20 requests/day/model free tier, verified from the 429 body | probe script |

Not verified: a full 48-case run after the final fixes (quota), and a real browser screenshot
(Chrome extension not connected to the session).

| Loop 1: page 51 attribution (live, gemini-3.5-flash-lite) | quoted definition attributed to Western scholars; audited; 14 s; junk-piece scan 24 -> 18 | server :786 |

| UI redesign (headless Chrome screenshots) | welcome light/dark, conversation, reference card render correctly; ﷽ fits arch; Urdu titles isolated | eval/ui-*.png |
| Detailed answer, Misaq-e-Madina (live, flash-lite) | 583 words, 6 pages, audited, 27 s, no 'book says' phrasing | server :786 session showcase1 |

| Loop 2: Hindi Misaq question (live, gemini-2.5-flash) | 535 words, wrong-script 0.0, 7 distinct pages, audited, 19.7 s | server :786 session loop2hi2 |
| UI renderer headless test | numbered list continuation, citation chips, HTML stays text | `node tests/ui_markdown.test.js` |

| Book 2 indexing | 102 pages, 98 chunks, 4 logo pages; segment build 20261116-121031 validate ok (3 784 / 759) | ingestion-report.json |
| Book 2 live answers | Hinglish takhleeq 514 words/10 pages; English Darwin 819 words/9 pages; both audited | server :786 sessions book2a, book2b |
| Book 1 regression (Urdu Misaq) | 445 words, audited, book-1 pages only | session book1c |
| Embedding identity after moving Ollama to C: store | cosine 1.0 vs cached vector | session check |

| "Tissues and Body Form explain this in detail" (live) | before: out_of_scope refusal, books not searched; after: 312 words, p.73, audited, 16.8 s | sessions tissue1-4 |

| Off-topic handling (live) | C code -> out_of_scope 3.5 s, no passages; bicycle chain -> not_in_library, no passages; Karbala -> not_in_library; Darwin control answered 713 words | sessions oos1, oos3x |
| Loop 3 benchmark extension | 60 cases incl. 12 Creation of Man; book-aware scoring | eval/book_benchmark.jsonl |

## Verification — 2026-11-17 agent & GenAI upgrade

**Offline.** `.\.venv\Scripts\python.exe -m pytest -q` → **250 passed** (231 before; 19 new in
`tests/test_agent_features.py`: follow-up parsing, outline suggestions, style notes, cloud-only
follow-up request, scope note, request validation, end-to-end follow-ups and scope flag,
needs_topic suggestions, scope predicate, BM25 `keep`, scoped search + sweep, retriever fallback,
setup check offline/secret-free). `node --check frontend/app.js` OK; `node tests/ui_markdown.test.js`
OK including complete and half-streamed `<<next` markers.

**Environment.** `.\doctor.ps1` reported Ollama `[FAIL]` (it was not running) and server `[WARN]`;
after `ollama serve` + server start, `GET /health/setup` → `ok`.

**Live HTTP** (server :786, saved mode Gemini; scratch script, sessions `live-36764a7b1c`,
`live-d96d633445`, `live-9691d73e47`):

| Question | Options | Result | Latency |
|---|---|---|---|
| Misaq-e-Madina kya tha? | style short | grounded, audited, 159 words, 8 pages, 3 model follow-ups, no marker leak | 117.7 s |
| Give a summary of “Development of Human Bones” | style points, scope Creation of Man pp. 70-76 | `scope.applied=true`, cited pages 71-75 only, audited (2 sentences fixed), 378 words | 207.3 s |
| mujhe kuch explain karo | — | `needs_topic`, 3 chapter-topic follow-ups | 11.1 s |

Trace of the scoped question: `explain` on `gemini-3.5-flash` failed with **ReadTimeout** (180 s),
then `gemini-2.5-flash` answered; audit on `gemini-3.1-flash-lite` 4.1 s. This motivated the 60 s
`stream_read_timeout`. **The new timeout has not yet been re-measured live.**

**UI.** Headless Chrome screenshots: `eval/ui-v2-guide.png` (guide dialog), `eval/ui-v2-answer-short.png`
(follow-up chips, "Same question" buttons, Download/Print), `eval/ui-v2-answer-scoped-dark.png`,
`eval/ui-v2-welcome.png`. Not verified: clicking through the chapter explorer in an interactive browser.

**Handover automation.** `tools/handover_snapshot.py` pipe-tested from another working directory
(exit 0, block written); `.claude/settings.json` parsed and contains the Stop and PreCompact commands.
Whether Claude Code has loaded the new hooks in the current session was not verified (may need `/hooks`).

## Verification — 2026-11-17 (2): voice input, English UI, welcome popup and tour

- Offline: `pytest -q` → **254 passed** (+4 in `tests/test_voice.py`: text-only `/transcribe` that
  must not call `ask`, language hint forwarding, empty audio 422, Whisper language map).
  `node --check` on `app.js` and `tour.js`; `tests/ui_markdown.test.js` OK.
- **Real Chrome (Claude in Chrome extension), page state via JavaScript, microphone stubbed** (no real
  audio recorded):
  | Case | Result |
  |---|---|
  | Double tap while the permission prompt is open | cancelled; 0 recorders created; bar hidden |
  | Tap, 1.6 s, tap again | recording → transcribing → idle; transcript in the question box; `/transcribe` 1 call, `/chat` 0 calls |
  | Tap shorter than 0.7 s | discarded, no transcription call |
  | Cancel button while recording | discarded |
  | Esc while recording | discarded |
  Voice bar seen in a screenshot: red dot, timer 0:05, Stop, Cancel.
- Welcome popup on a cleared profile: opens in English; choosing हिन्दी re-rendered title, buttons and the
  header 🌐 label, stored `mufti-ui-lang=Hindi`; the tour started in Hindi, ArrowRight advanced, Esc ended it;
  Guide rendered in Hindi with 10 steps. Test keys were then removed from the browser's localStorage.
- Tour placement in real Chrome (1536×730): mic at (414, 641), spotlight at (406, 633) — exact.
  Headless-Chrome screenshots offset the composer ~100 px (kept only `eval/ui-v3-welcome-en.png`,
  `eval/ui-v3-welcome-ur.png`, `eval/ui-v3-tour-5-hindi.png`, which are not affected).
- NOT verified: a real spoken recording through local Whisper (needs the user's voice).

## Verification — improvement loop iteration 1 (2026-11-17): answer feedback
- `pytest -q` → **258 passed** (+4 `tests/test_feedback.py`: save + summary + answer trimmed to 1500
  chars; invalid rating/reason/empty question/bad session rejected; torn last line tolerated; drafts are
  `reviewed:false`, skip known benchmark questions, carry no expected pages).
- Real Chrome: saved answer → 👎 → "Incomplete" + note → Send → form closed, "Thanks…" shown;
  `/feedback/summary` returned total 1, reason incomplete, cited pages 383…330. The test entry was then
  deleted (`data/feedback/feedback.jsonl` removed) so no fake feedback remains.

## Verification — improvement loop iteration 2 (2026-11-17): saved answers
- `pytest -q` → **261 passed** (+3 `tests/test_saved.py`: save/dedupe/newest-first/open/delete;
  validation and bad ids → 404/422; corrupt file reads as empty).
- Real Chrome on a saved conversation: ☆ Save → "★ Saved", sidebar count 1 → Saved answers view with
  1 card → search "zzzz" shows "No saved answer matches", "bones" shows it → Open renders 5 headings,
  19 citation chips, 5 sources → Delete asks "Click again to delete" → second click removes it
  (server count 0). Test data file removed afterwards.

## Verification — improvement loop iteration 3 (2026-11-17): Quiz me
- `pytest -q` → **266 passed** (+5 `tests/test_quiz.py`: only cited sentences become statements;
  validation keeps a supported question and drops an invented date, a bad statement id, duplicate
  options and an out-of-range answer; one structured call on the `quiz` task with statements only;
  short answers refused; route 404 for unknown answer, 409 for ungrounded, 422 for bad session id).
- The first version of the check let the invented-date question through (plain word overlap matched
  "was"); fixed before shipping — recorded here because it is exactly the failure the check exists for.
- Live (`live-36764a7b1c`, "Misaq-e-Madina kya tha?", Hinglish): `POST /quiz` 200 in **4.6 s**, provider
  gemini (quiz lite models), 7 statements, **3 of 4 questions kept**, citations [1,2]→pp. 383/407,
  [1,5]→383/352, [6]→321.
- Real Chrome: 🧠 Quiz me → 3 questions in Hinglish → choosing an option shows "✓ Sahi", the reason,
  page chips [1][2] and "Score: 1 / 1".

## Verification — improvement loop iteration 4 (2026-11-18): first-question speed
- Before (live, "Misaq-e-Madina kya tha?", short, server freshly restarted): total **65.0 s** =
  language 1.6 s + **retrieve 42.5 s** + explain 16.5 s + audit 2.7 s; models: flash-lite-latest,
  gemini-3.5-flash (no stall — the 60 s stream timeout was not triggered), 3.1-flash-lite.
- Profile in one fresh process: import 4.0 s, segments 0.1 s, BM25 index 0.6 s, embedding with server
  options 18.8 s (model reload), first Chroma query 7.6 s, full search #1 7.2 s, **#2 0.33 s**.
  Direct Ollama: cold bge-m3 10.1 s, warm 1.6-1.8 s.
- After the change: `/health` warmup `ready` in 6.28 s (corpus 0.14, bm25 1.05, embedding 2.89, vector 2.2);
  same question → total **41.4 s**, **retrieve 3.25 s**, explain 30.0 s, audit 2.8 s.
- Offline: **270 passed** (+4 `tests/test_warmup.py`; conftest disables the real warm-up in tests).

## Verification — improvement loop iteration 5 (2026-11-18): Topic index
- `pytest -q` → **271 passed** (+1: concepts come from the reviewed lexicon; contents pages skipped;
  chapter/section kind, parent chapter and page ranges correct).
- Real Chrome: ▦ Topic index → 10 concepts, 361 sections, other views hidden, breadcrumb "Topic index".
  Searches before the fix: "bones" 2, "سیرت" 308, "equality" 0, "madina" 0 sections. After adding
  cross-script matching: "equality" → 2 (آئینی مساوات کا حق, حقوق میں برابری), "madina" → 4
  (دستور مدینہ …), "constitution" → 6. Explain was not clicked (no Gemini call needed for this check).

## Verification — improvement loop iteration 6 (2026-11-18): directions + cache revalidation
- First real-Chrome check after editing tour.js still showed 7 tour steps: the browser had cached the old
  file (no Cache-Control header). Fix: `Cache-Control: no-cache` for `/`, `.js`, `.css`, `.html`
  (`curl -D -` shows `etag` + `cache-control: no-cache`). New test in `tests/test_storage.py`; **272 passed**.
- After reload, for English / Hinglish / Urdu / Hindi: `tr('tour').length` = 9, the step after the library
  is "Find any topic" / "Koi bhi topic dhoondiye" / "کوئی بھی موضوع تلاش کیجیے" / "कोई भी विषय खोजिए",
  Guide renders 12 steps including "Quiz me". Test language/tour keys restored in localStorage.

## Verification — improvement loop iteration 7 (2026-11-18): accuracy
- Trace analysis (84 explain traces): audit ran on 81 (2 local, 1 quota); it changed 61 and removed
  12 of 957 sentences (issues: unsupported 66, misattributed 5, overstated 3, contradicted 2); 119
  uncited sentences in 51 answers.
- Residual baseline (`eval/residual-audit-before.json`, judge gemini-2.5-flash, 6 final answers):
  **3/62 sentences flagged (4.8%)** — 1 unsupported, 1 misattributed, 1 overstated; judge time 8.5-25 s.
- First live run of the new audit: all 3 answers "citations_checked" (NOT audited). Causes found in
  the traces: (1) Gemini HTTP 400 "too many states" on the bounded audit schema; (2) that failure
  tripped the Gemini breaker, so the lite audit was skipped and the next question went to qwen3:1.7b
  (216 s, explanation_unverified). Both fixed; tests `test_audit_schema_has_no_bounds_in_add_citations`,
  `test_failing_strong_audit_does_not_trip_the_provider`.
- Second live run: Western scholars (English) → strong tier, 22 sentences, 30 s, 2 changed, **3 citations
  added**; Hijrat (Hinglish) → strong timed out at 40 s on 42 sentences → lite, 2 changed, 1 citation
  added, 2 number flags; Urdu creation question → strong timeout on 39 sentences → lite, 4 changed,
  **2 non-verbatim quotes un-quoted**. All 3 **audited**.
- Parallel chunking added for long answers (offline test: 42 sentences → 3 chunks of 14, each judged once).
  Live re-check: Gemini overloaded (3.5-flash 503, 2.5-flash 429, 3-flash-preview 503); the answer came
  from 3.5-flash-lite and was audited by the lite tier — chunked strong audit NOT yet exercised live.
- Independent re-judging with gemini-3-flash-preview failed (ReadTimeout / HTTP errors on all 4) —
  **before/after accuracy comparison not measured yet**; listed first in TASKS.md "Open now".
- Offline: **281 passed**.

## Verification — improvement loop iteration 8 (2026-11-18): photo / file input
- OCR model comparison on scanned pages (150 dpi render): page 257 — `urd` 40, `urd_naw` **72**, `urd-best` 38
  Urdu words; page 51 — 58 / **86** / 52. `urd_naw+eng` is now the Urdu/Auto default.
- Page finder on "photos" (130 dpi renders) of 4 real pages: Muqaddima 257 and 51, Creation of Man 73 and 40 —
  **4/4 found at rank 1**, OCR 2.3-3.0 s each, no model call.
- One `/api/embed` 400 seen during the first try did not reproduce with the same inputs (recorded as transient).
- Real Chrome: synthetic drag & drop of a canvas "photo" → overlay shown/hidden → `/extract` 0.47 s → card with
  3 actions → Find → Creation of Man p. 73 Strong match (+ p. 4 contents, 53, 59, 75). Explain this → "Fully answered
  from the book", "Fact-checked against the book", 9 citation chips.
- Offline: **289 passed** (+8 `tests/test_attach.py`). Camera capture NOT tested (no camera in this session).

## Verification — loop tick 2026-11-18 ~01:15: residual accuracy, second strong judge
- `eval/residual_audit.py` now calls the judge directly (Gemini 3: thinkingLevel=low, 240 s, one retry):
  through the app client gemini-3-flash-preview timed out; directly it answered in 2.3 s (low) / 7.4 s (default).
- Judge gemini-3-flash-preview, AFTER (4 newest answers; 1 call failed): 3 answers, **7/58 flagged (12.1 %)**.
  Manual check against the cited pages: Fatty Acids / Amino Acids / Nitrogen Gases ARE on p. 52 (judge false
  positives, 3); "Poly Saccharides" belongs to a different list on that page (**real error**); the Hijrat sentence
  about alliances with Bedouin tribes is not on p. 276 (**real error**). All flagged answers had been audited by the
  LITE tier because gemini-2.5-flash's daily quota was exhausted.
- Judge gemini-3-flash-preview, BEFORE (6 older answers): only 2 succeeded (4 HTTP errors) → 0/27 flagged.
  **Sample too small and judges differ from the 4.8 % baseline: no before/after conclusion is drawn.**
- Change: second strong judge `gemini-3-flash-preview` (low thinking) after `gemini-2.5-flash` in
  `task_models.audit_strong`; test `test_strong_audit_on_gemini3_uses_low_thinking`. **290 passed.**
- Live check of it: both strong models now return 429 (free-tier quota) → lite tier used. Strong path and chunking
  remain unverified live until the quota resets (~13:30 IST).
