# Product requirements: Mufti AI
## Purpose
Help the owner explore their uploaded Islamic books in English, Urdu, Hindi and Hinglish, with verifiable source citations and a clear choice of model.

## Required behavior
1. Run from D:\mufti-ai at localhost:786 and retain the PDF, index and conversations across restarts.
2. Search all indexed passages, handle common name spellings and multilingual queries, and answer questions when the book contains adequate readable evidence.
3. Never manufacture an answer merely to achieve universal answer coverage. Explain whether search, evidence, verification or model availability prevented an answer.
4. Provide Auto, preferred cloud and local-only modes. Try configured clouds in order before the chosen Ollama fallback. Show selected and actual model names distinctly before, during and after generation.
5. Persist new response citations/model metadata in history. Preserve old conversations.
6. Support original-page inspection, text entry, local microphone transcription, dark mode and responsive layout.
7. Keep keys server-side; disclose cloud processing of question/context/excerpts. Local mode does not generate through clouds.
8. Maintain runnable source, tests, operating commands and AI handover documentation.

## Acceptance criteria
- Saved model selection is visible without reopening settings and applies to the next request.
- Simulated quota exhaustion reaches the selected local model; an actual local model response is verified.
- Known answerable book questions produce supported claims and real page citations. Unknown questions produce no fabricated citations.
- History reload retains new response evidence/model badges.
- A subsequent AI can start the app, locate source/data, run tests and identify outstanding work using Handsover.md.

## Quality evaluation
Measure verified-answer coverage on a manually checked, multilingual book question set, citation accuracy, retrieval recall, latency and truthful failure reporting. Unit tests and one live success do not establish full-book coverage. A stronger model and corrected OCR may be needed for some passages.

## Exclusions
No general-knowledge answers presented as book evidence, public multi-user hosting, autonomous purchases, quota bypasses or authoritative personal religious rulings.

## Bibliographic acceptance checks
An author question about the uploaded book must return its visually verified author and PDF page citation even without available cloud quota. Typographical title variants must match conservatively; unrelated titles and ambiguous books must not receive another book's author. Changed source files must invalidate reviewed facts. Publication details are separate from generated substantive answers.

## Status against the acceptance criteria — 2026-11-12

| Requirement | State |
|---|---|
| Runs at localhost:786, retains PDF, index and conversations | **Met.** Verified live this session. |
| Searches all indexed passages, handles spellings and multilingual queries | **Met and measured.** Reviewed page reaches the answering model on 81.0% of answerable benchmark questions, up from 64.3%. |
| Never manufacture an answer; explain what prevented one | **Met.** Distinct reason codes, and two new code-level guards reject fabricated and misattributed claims. |
| Auto / preferred-cloud / local-only modes, selected vs actual model shown | **Met.** Provider labels are honest; no blanket "Ready". |
| New responses persist citations and model metadata | Met previously; not retested this session. |
| Original-page inspection, text entry, local transcription, dark mode, responsive | Met previously; **not retested in a browser this session.** |
| Keys server-side, cloud processing disclosed | Met. Only `GOOGLE_API_KEY` is set and it is quota-exhausted. |
| Runnable source, tests, commands, handover docs | **Met.** 133 offline checks pass. |
| Known answerable book questions produce supported claims and real page citations | **NOT met for broad content questions on local hardware.** See below. |

### The one requirement not met, stated plainly
A broad content question such as `Explain Gender Equality in detail` does **not** yet produce a
verified scoped answer on this machine. Retrieval is correct — the two reviewed pages are the
top two evidence windows in 2.6 s — but the local 1.7B-3B model drafts claims that fail honest
verification: it omits the attribution the book's quoted sources require, and it draws claims
from adjacent-concept pages. All such claims are now rejected, so the product refuses honestly
and shows the relevant pages as related material instead of fabricating. That refusal is the
correct behaviour under requirement 3, and it is still not the answer requirement 2 asks for.

The gap is model capability on a 2 GB GPU, not retrieval, not grounding and not the book. A
capable model with the same evidence would answer correctly; the same page-50 text supports a
properly attributed claim, which the regression tests demonstrate. Cloud generation could not be
exercised because the configured Gemini key returns a real HTTP 429.

### What this means for the product
On local-only hardware this is reliably a **sourced reading aid**: it finds the right pages fast,
quotes them exactly, links to the scan, scopes partial coverage, and refuses rather than
inventing. It is not yet a reliable answer generator for broad questions. Treat usable cloud
quota, or a stronger local model than a 2 GB GPU can hold, as a product requirement for that,
and do not close requirement 2 by weakening verification.

### Revised non-functional expectation
Bibliographic questions answer in about 1 second. Content questions take tens of seconds to
minutes locally, because the local model generates at 1.6-3.0 tokens/s. Progress must stay
visible throughout; a silent wait is a product defect even when the pipeline is healthy.


## Requirement clarifications settled by measurement, 2026-11-13

### The product promise, restated

When the answer is in the book, find the relevant material and **explain it** in the reader's
language — not paste quotations. Every factual statement, interpretation and conclusion stays
supported by the book's actual context, keeping its distinctions, qualifications and
attribution. This is now enforced by code, not only requested in a prompt: see Rules.md.

### Partial is a first-class outcome

The book has no general treatment of equality between men and women. It has a quoted Western
analysis on PDF page 50 and one Charter of Madinah article about adult franchise on page 257.
The correct product behaviour is a **scoped partial answer plus an explicit list of what is
missing** — not a full-sounding answer, and not a refusal. Any future benchmark case whose
expectation is `answerable_partial` is testing exactly this.

### "I could not explain this" is not "the book does not contain this"

These are separate outcomes with separate copy, separate reason codes and separate UI text.
Reporting a model, index, OCR, timeout or verifier failure as an absence of evidence in the
book is a correctness bug, not a wording preference.

### Accuracy is not negotiable against answer rate

A measured example from this session: relaxing one verifier instruction raised the answer rate
and immediately produced the claim *"Gender equality is a fundamental principle in Islam,
emphasizing the equal rights and responsibilities of men and women in all aspects of life"*
from a span that calls gender equality a point of **difference** between Islam and the West.
That is worse than no answer, because it is a plausible-sounding religious statement the book
never makes. Guards may be scoped to remove false refusals; they are not loosened to raise
coverage.

### Cloud and local are different products, and the UI must say which ran

A capable cloud model produces the full scoped explanation in about 50 seconds. The 2 GB local
GPU, on the same evidence and the same guards, produces either a shorter verified answer or
the labelled excerpt fallback. Both are honest. The interface already shows the selected
provider/model, the model that actually answered and the fallback reason, and that must keep
working — a configured API key is not proof a service is ready.

### Acceptance targets are measured engineering targets

They are reported with their denominators, their configuration (provider, evidence windows,
tree route) and whether the calls were live or mocked. Retrieval recall and explanation
correctness are reported separately, because a retrieved page is not an answer. See
VERIFICATION.md.

## Requirement update — 2026-11-16 (from the user, verbatim intent)

"Whatever I ask, I will ask from the book — so it must not refuse when the answer is in the
book. Explain properly, with respect, like ChatGPT/Gemini explain. Make it industry level."

Acceptance criteria now in force:

1. Every answerable benchmark case receives a grounded, cited answer (`eval/explain_eval.py`,
   `false_refusals` empty), measured on the cloud route with the provider named.
2. `absent` cases are not answered as if the book covered them (`answered_absent` empty).
3. At least one cited page of an answered case is a reviewed expected page (page-hit rate).
4. Answers are structured (direct answer, sections, bullets, summary), in the reader's
   language, with ﷺ and adab; every factual sentence links to its page.
5. Cloud answers are fact-checked sentence by sentence; anything else is labelled.
6. Streaming: the reader sees text within seconds on cloud, and the live draft on local.
7. Model visibility rules (selected vs answering model, fallback reason) unchanged.

## Requirement update — 2026-11-17 (from the user)

"Agent ko bade level pe accha karo", easier and more detailed, with directions for new users and a
handover that is always current. Accepted requirements:

1. Readers choose how an answer is written (detailed / short / simple / study notes) without any
   loss of grounding or fact-checking.
2. After every answer the reader is offered relevant next questions from the same books; a vague
   question is answered with the books' real topics, not a dead end.
3. Readers can study a chapter or section (explain, summary, focus) using the books' outline.
4. A new user can find out what is missing on their computer and how to fix it, in Hinglish,
   both in the app and from PowerShell.
5. Answers can be saved (.md) and printed.
6. Any AI can take over: AGENTS.md entry point; feature recipes (ADD_FEATURE.md); repair prompt
   and triage (REPAIR_PROMPT.md); facts in Handsover.md refreshed automatically when a session stops.

Non-goals unchanged: public hosting, user accounts, rulings beyond what the books say.
