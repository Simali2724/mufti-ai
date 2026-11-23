# ADD_FEATURE.md — how to add a new feature safely

Use this when you (or another AI) want to add something new to Mufti AI. Part A is a copy-paste
prompt for an AI; Part B is the anatomy of the app (where each kind of change goes); Part C gives
step-by-step recipes with real examples; Part D is the definition of done.

---

## Part A — Copy-paste prompt for any AI

```text
You are working on Mufti AI in D:\mufti-ai (Windows, Python 3.12, FastAPI + LangGraph, vanilla JS UI).
First read AGENTS.md, then Handsover.md (top: auto-snapshot + CURRENT STATE), TASKS.md, Rules.md,
Architecture.md "At a glance", FEATURES.md and ADD_FEATURE.md.

FEATURE TO ADD: <describe it in one paragraph — who uses it, what they see, what it must never do>

Constraints:
- Book answers stay grounded: every factual sentence cited [n], audit unchanged or stronger.
- No new model call per question unless you MEASURE its benefit (2 GB GPU; Gemini free tier is
  ~20 requests/day per model). Prefer zero-cost signals (same-call markers, book outline, code).
- Never print or send .env secrets; never rebuild/delete data/index, data/books, data/book-metadata.
- Back up every file you change into backups/<feature>-<yyyymmdd>/ first.
- Keep strict mode (answer_mode='strict') and all existing tests passing.

Deliver:
1. Code in the right layer (see ADD_FEATURE.md Part B), small and commented with the WHY.
2. Offline tests in tests/ (mock models like tests/test_explain.py FakeModel) — both directions:
   the feature works, and it cannot weaken grounding.
3. Run: .\.venv\Scripts\python.exe -m pytest -q ; node --check frontend\app.js ; node tests\ui_markdown.test.js
4. If live behaviour matters: one live check against the running server, with the result recorded.
5. Docs: FEATURES.md row, USER_GUIDE.md (if users see it), Architecture.md (if data flow changed),
   TASKS.md, Handsover.md CURRENT STATE, VERIFICATION.md (what you measured).
Report honestly what was tested live vs offline and what is not done.
```

## Part B — Anatomy: where does my change go?

| Kind of change | Layer | Files |
|---|---|---|
| New request option (e.g. a toggle) | API schema → graph input → agent | `app/core/schemas.py` (`ChatRequest`), `app/agents/graph.py` `_ask()` initial state, `app/agents/state.py` |
| New response field | schema → graph → UI | `ChatResponse` in `schemas.py`, set in `graph._ask()`, and in `formatter.run()`'s history `turn` so reloaded conversations keep it |
| Change how answers are written | prompt / explain agent | `app/llm/prompts.py` `EXPLAIN_RULES`, `explain_agent.user_message()` (per-request notes like `STYLE_NOTES`) |
| Extra info from the model **without an extra call** | hidden marker in the same answer | follow the `<<next: … >>` pattern: ask in `user_message`, strip in `explain_agent.run()` **before** `split_marker`/audit (see `suggest.split_followups`), strip in UI `stripMarkers()` |
| New pipeline step | LangGraph node | write `async def run(state) -> dict` in `app/agents/<name>_agent.py`, add to `nodes` and edges in `graph.build_graph()` |
| Search behaviour | retrieval | `app/retrieval/hybrid.py` (routes, fusion), `evidence.py` (window selection, floors), `retriever_agent.py` |
| New provider / model routing | LLM layer | `app/llm/providers.py` (HTTP), `app/llm/router.py` (order, alternates, cooldown), `config.yaml` |
| New read-only endpoint | admin routes | `app/api/routes_admin.py` (keep heavy work in a module, import inside the function) |
| UI control / panel | frontend | `frontend/index.html` (markup), `app.js` (logic; build DOM with `element()` and text nodes — **never innerHTML with model/book text**), `style.css` (append; use CSS vars, add `.dark` variants) |
| Setup / environment check | doctor | add a `check_*` function in `app/core/setup_check.py` returning `item(...)` with `fix` + `fix_hinglish` |
| Reviewed book facts | data | `data/book-metadata/<book_id>.json` (reviewed only; see Rules.md 13) |

**State contract.** Agents communicate only through `AgentState` keys. Anything per-turn
(e.g. `answer_style`, `scope`, `followups`) must be **set in the initial input of `_ask()`**,
otherwise the LangGraph checkpoint carries the previous turn's value into this one (a real bug of
2026-11-16).

## Part C — Recipes (with real examples from the 2026-11-17 upgrade)

### C1. A new answer style (example: `answer_style`)
1. `schemas.py`: extend `AnswerStyle = Literal[...]`.
2. `explain_agent.py`: add the instruction to `STYLE_NOTES[...]` — it must restate that citations stay mandatory.
3. `index.html`: add an `<option>` to `#style`; `app.js` `styleActions` if it should be a quick re-ask button.
4. Test: `tests/test_agent_features.py::test_style_note_is_added_only_for_non_default_styles`.

### C2. Same-call model output (example: follow-up questions)
1. Ask for a hidden marker at the END of the answer (`FOLLOWUP_NOTE`), only when it is cheap (cloud).
2. Parse and remove it before parsing coverage and before the audit (`suggest.split_followups`).
3. Validate in code (length, no citations, dedupe) — model output is data.
4. Have a deterministic fallback (book outline) so local models get the feature too.
5. Strip partial markers from the live draft in `app.js` `stripMarkers()`; add a case to `tests/ui_markdown.test.js`.

### C3. Restricting search (example: chapter `scope`)
1. Thread the option: `ChatRequest.scope` → `_ask()` → `state['scope']`.
2. Filter inside each retriever route (`hybrid.in_scope`), without rebuilding indexes (`bm25.search(keep=...)`).
3. **Honest fallback**: if the scope finds too little, search everything and report `scope.applied=false`; the UI says so.

### C4. A new endpoint + UI panel (example: chapter explorer)
1. Pure function in a module (`suggest.outline`) → thin route (`GET /books/{id}/outline`).
2. UI: fetch, build DOM with `element()`; buttons call `send(question, {scope, style})`.

### C5. A new agent node (template)
```python
# app/agents/my_agent.py
"""What it does, WHY it exists (the measured problem), what it costs."""
from app.core import diagnostics

async def run(state):
    ...                                   # read only the keys you need
    diagnostics.record('my_agent', ...)   # leave a trace for debugging
    return {'my_key': value}              # return only changed keys
```
Wire it in `graph.build_graph()`: add to `nodes`, then an edge or conditional edge. Add `my_key` to
`AgentState` and to `_ask()`'s initial state if it is per-turn.

## Part D — Definition of done

- [ ] Backup in `backups/<feature>-<yyyymmdd>/`
- [ ] Offline tests added; full suite passes (`pytest -q`), `node --check`, `ui_markdown.test.js`
- [ ] Grounding unchanged or stronger (no prompt/audit relaxation, no unvalidated model text shown as fact)
- [ ] Works in all four languages (English, Urdu RTL, Hindi Devanagari, Hinglish) and dark mode
- [ ] Works when the answer comes from the local model and when no cloud key exists
- [ ] Live check done (or explicitly listed as NOT done in Handsover.md)
- [ ] FEATURES.md, USER_GUIDE.md, Architecture.md, TASKS.md, Handsover.md CURRENT STATE, VERIFICATION.md updated
- [ ] `tools/handover_snapshot.py --tests` run at the end

## Feature ideas backlog (not built yet — pick from here)

| Idea | Value | Notes / cost |
|---|---|---|
| ~~Quiz / self-test from an answer's sources~~ **BUILT loop 3** | learning | one extra model call; generate Q&A only from cited passages, audit answers |
| ~~Bookmarks / saved answers page~~ **BUILT loop 2** | convenience | frontend + small JSON store in `data/` (not localStorage only) |
| Compare two books on one topic | depth | scope per book, two retrievals, one explain call with both source sets |
| ~~Glossary of Arabic/Urdu terms~~ → **Topic index BUILT loop 5** (no generated definitions; a real glossary still needs human-reviewed definitions) | learning | build once offline from `concept-lexicon.json` + outline, review by human |
| ~~Per-answer feedback (👍/👎 + reason) → eval cases~~ | quality loop | **BUILT 2026-11-17 loop 1** (`app/core/feedback.py`) |
| OCR correction workflow for the 28 low-quality pages | accuracy | `data/book-corrections/` is already read by the code |
| Paid-key / quota dashboard | reliability | show per-model 429 cooldowns from `router._model_cooldown` |
