# Design specification
Filename intentionally matches the user's requested Desgin.md.

## Experience
Mufti AI is a personal Islamic book assistant. Warm ivory and emerald surfaces, restrained gold accents, readable typography, optional dark mode. Urdu answers use RTL and Nastaliq fallback fonts; Hindi/English/Hinglish retain appropriate direction. Layout adapts to narrow screens through the menu drawer.

## Model visibility
The composer always shows Selected mode/model and the first configured provider expected to run. Clicking this strip opens Models & fallback. The settings dialog edits provider order, cloud model IDs and installed local chat models. The UI must distinguish planned routing from actual execution: live status names task/provider/model; completed messages provide Models actually used. Refusals also show successful search/routing model calls. New history entries retain this metadata and citations across reloads; older entries remain readable.

## Answer states
Searching, generating, verifying, complete, no matching passages, related passages without direct answer, verification failure, and service failure must be distinguishable. Do not represent a model outage as a factual absence from the book. The response-language selector is explicit: choosing Urdu causes Urdu replies even to English questions; Auto detects the question script/language.

## Source interaction
Each verified claim includes an application-generated source number. Citation details show an exact bounded excerpt, physical PDF page and original PDF link. OCR labels prompt checking the scan. No invented page numbers or quotes. Evidence absence should encourage a narrower question or wording from the book.

## Accessibility and privacy
Use labelled controls, keyboard-accessible dialogs, visible focus, textContent for untrusted strings, readable error text and responsive wrapping for model IDs. Cloud settings disclose question, recent context and selected excerpt processing. Keys are never entered into or returned by the browser. Never label cloud generation as local. Keep settings/status requests non-generative.

## Direct publication facts
For author/title/publisher/ISBN/first-publication responses, show Verified book details and state that the answer came from visually checked PDF pages without model generation. The selected model remains visible for ordinary questions. Reviewed transcription must be labelled separately from raw OCR in source details. A failed draft must not say Answered by as if it succeeded.

## Coverage states after the 2026-11-12 repair

### Three outcomes, each visually distinct
- **Full / partial coverage.** Sectioned answer, each claim carrying its own source number.
  Partial coverage opens with "The book covers part of this question:" and ends with a
  "Not covered in this book" list naming the aspects the excerpts do not reach, so a broad
  question gets a scoped answer rather than a refusal or an over-claim.
- **No direct answer.** The reader is told plainly that the indexed book does not directly
  answer the question, followed by "Related passages (these do not directly answer the
  question)" with real page links to read. This is a useful outcome, not a dead end: the
  reader can open the page and judge for themselves.
- **Service failure.** A distinct message naming the actual problem (quota, provider down,
  embedding/search service down) and stating explicitly that it is a service failure and not a
  statement about the book. Never phrase a model or quota problem as absence of evidence.

Related material is never styled or labelled as a verified answer, and never contributes a
citation number.

### Honest latency expectations on local hardware
On a 2 GB GPU a content question takes tens of seconds to minutes because the local model
generates at 1.6-3.0 tokens/s. The SSE status stream must therefore keep naming the current
task and the elapsed time; a silent spinner is indistinguishable from a hang. Bibliographic
questions answer in about a second through the reviewed-facts path, so the interface should not
imply every question is equally fast.

### Attribution is part of the answer, not a footnote
When a passage quotes a named outside writer, the answer must say whose statement it is. The
book quotes Ronald Inglehart and Pippa Norris on gender equality; presenting that as the
author's own conclusion misrepresents the book. The evidence given to the model names the
writers a passage quotes, and verification rejects a claim drawn from such a passage that does
not name them. Source details continue to distinguish reviewed transcription from raw OCR.

### Concept boundaries are visible to the reader
"Gender equality", "constitutional equality" and "protection of women's rights" are adjacent but
different ideas, and the book treats them in different places. A passage about one is not shown
as support for a question about another; it may appear as related material instead. The reviewed
concept lexicon is what draws those boundaries, so adding a concept there is a content decision
with user-visible effect and needs the same review as any other reviewed fact.

## What the reader sees after the 2026-11-13 repair

### An explanation, not a wall of quotations

The answer opens directly with the supported points, grouped under short headings, each
sentence in the assistant's own words and each carrying its citation marker. Two rules now
enforce that shape in code rather than hoping the model obeys the prompt:

- A claim that reproduces its source sentence is refused, because the source text is already
  shown to the reader under **Sources** and repeating it wastes the answer.
- A claim is one sentence. A claim that makes two statements cannot be verified as one.

### The book's own hedging survives into the answer

Where the book says something "could plausibly" be so, the answer says so too. A claim that
restates a tentative source statement as settled fact is refused and sent back to be
rewritten. This matters most on quoted outside opinion, where flattening a hedge turns a
researcher's suggestion into the book's ruling.

### Attribution is visible, and it is the book's own

Where a passage quotes a named writer, the answer names them. If the drafting model omits the
names, the code supplies them from the book's own citation line, in the reader's language:

> **As quoted from Ronald Inglehart and Pippa Norris:** the analysis of these social attitudes
> reveals a significant gap between Islamic and Western values.

The reader can therefore tell, without opening the PDF, whose statement they are reading. A
sentence printed after the citation that closes a quotation is the book speaking in its own
voice and is not dressed up as someone else's.

### Three different kinds of "no answer", never conflated

| What the reader sees | When |
|---|---|
| Partial answer, with **Not covered in this book** listing the gaps | Some of the question is supported |
| **"A generated explanation could not be verified… These are source excerpts, not an explanation."** followed by the book's own words with working page links | The book carries material on the topic but no drafted sentence survived verification |
| "The search finished and the passages it found do not cover this question." | Searching completed and the material genuinely is not there |
| "No answering model could be reached… this is a service failure, not an absence of evidence" | Provider or quota failure |

The third and fourth were previously capable of reading as "the book is silent", which is the
single most damaging thing this application can say wrongly. The excerpt fallback is labelled
as excerpts so it is never mistaken for a generated explanation.

### Excerpts show the part that concerns the question

PDF page 257 prints fifteen Charter of Madinah article titles as one unpunctuated run. It is
now split into separate spans, so the citation shows
`(Adult Franchise) (No Gender Discrimination in Adult Franchise)` rather than the first title
on the page, `(Conditional Superordination of State)`. The same selection drives the related-
passages list.

### Headings are real headings

Chapter and section labels beside a citation come from the PDF outline and are correctly
spelled Urdu. Previously this field held whatever text topped the page: running headers, page
furniture, and on one page the publisher's street address.

## Explanation answers, 2026-11-16

- **Reads like a teacher, not a list.** A direct answer first, then `###` sections, bullet
  points, bold key terms and a short summary. Urdu renders right-to-left in Nastaliq, headings
  included.
- **Every statement is one click from the page.** `[n]` becomes a small chip; hovering shows
  the book and PDF page, clicking opens the page dialog with the OCR text and the original PDF.
- **The answer appears as it is written.** A gold cursor marks a live draft; when the
  fact-check finishes, the checked answer replaces the draft (it may differ slightly).
- **Honest verification badge.** "✓ Fact-checked against the book" only after the audit ran;
  "◌ Sources linked · not independently fact-checked" for local-model answers or when the
  audit model was unreachable.
- **Friendly progress.** "Writing a detailed answer from the book · Gemini / gemini-2.5-flash",
  "Checking every sentence against the book…", and "… is busy — trying the next option" on
  fallback, instead of raw task names.
- **Copy** puts the plain answer plus a page list on the clipboard.

## Islamic visual theme, 2026-11-16
Emerald (#0f4d3c / #0b3a2e) and gold (#b8923f) on ivory (#fbf7ee); eight-point-star girih pattern (inline SVG, 22% opacity) on page and sidebar; mehrab-shaped hero with ﷽ (Amiri) and Urdu tagline; answer cards with a gold top rule; ✦ before section headings; gold citation chips; emerald user bubbles; night-emerald dark mode with gold calligraphy. Screenshots: eval/ui-*.png.

## Design additions — 2026-11-17 (easier to use, more guidance)

- **Guide dialog** (header "? Guide"; opens on the first visit): three tabs — *Kaise istemal karein*
  (nine illustrated steps in Hinglish), *Setup check* (live checklist with ✓ / ! / ✕ and exact fixes in
  English + Hinglish), *Shortcuts*. "Don't open automatically" is remembered per device.
- **Answer style selector** (✎) beside the language selector: Detailed, Short, Simple words, Study notes.
- **"Aage poochhiye · Ask next"** under every answer: gold follow-up chips; below them
  **"Same question:"** chips to re-ask in another style. Visual weight stays below the answer and sources.
- **Download / Print** join Copy and Read aloud in the meta row; printing opens a clean serif page with
  the answer and numbered sources.
- **Chapter explorer** (My library → ☰ Chapters): collapsible chapters with page ranges; each chapter
  and section has *Explain*, *Summary* and outlined *◎ Focus*. Urdu titles render with `dir=auto`.
- **Focus chip** above the composer ("◎ Focus: … ×"), emerald, removable; an answer that fell back to
  the whole library says so in a note — scope is never silently ignored.
- **Starter topics** ("EXPLORE THE BOOKS") on the welcome screen, generated from chapter titles.
- All new elements have dark-mode variants and wrap on phones (≤760 px).

## Design additions — 2026-11-17 (2): English default, welcome popup, arrow tour, voice bar

- The interface text is **English by default** (hero "The light of knowledge, from your books.",
  placeholder, buttons). Example questions stay multilingual on purpose — they show what can be asked.
- **Welcome popup** on the first visit: ۞ mark, title, one-paragraph purpose, four large language
  chips (English, Hinglish, اردو, हिन्दी) that re-render the popup instantly, a note that only the
  directions change language, and *Skip* / *Show me around*. Urdu switches the popup to RTL Nastaliq.
- **Arrow tour**: the page dims except a gold-bordered spotlight on the target; a card with a rotated
  square arrow points at it (right of sidebar items on desktop, below/above elsewhere). "Step n of 7",
  Back / Next / Skip. Seven stops: question box → mic → answer style → new conversation → My library →
  Models → Guide.
- **🌐 language button** in the header shows the current directions language (icon only on phones).
- **Voice bar** above the composer: pulsing red dot, "Recording — speak now", tabular timer,
  red *■ Stop*, outlined *✕ Cancel*; turns gold while converting to text.
