# Run Mufti AI on Windows

> New here? Read **USER_GUIDE.md** (how to use) and run **`.\doctor.ps1`** first — it lists what is
> missing and how to fix it. For AIs/developers: **AGENTS.md**.

## Quick reference (2026-11-17)

```powershell
cd D:\mufti-ai
.\doctor.ps1                                   # setup check with fixes (add --json for machines)
.\start.ps1                                    # start the app -> http://localhost:786
.\.venv\Scripts\python.exe -m pytest -q        # offline suite (expect 250 passed)
node --check frontend\app.js; node tests\ui_markdown.test.js
.\.venv\Scripts\python.exe tools\handover_snapshot.py          # refresh Handsover.md facts
.\.venv\Scripts\python.exe tools\handover_snapshot.py --tests  # ... and run the suite into it
curl.exe -s http://127.0.0.1:786/health/setup                   # same check as doctor, over HTTP
curl.exe -s "http://127.0.0.1:786/suggestions?language=Hinglish" # starter topics from the outline
curl.exe -s http://127.0.0.1:786/books/<book_id>/outline        # chapters + page ranges
```
One question with the new options (PowerShell; style = detailed|short|simple|points):
```powershell
$body = @{question='Misaq-e-Madina kya tha?'; session_id='cli-test'; answer_style='short';
          scope=@{book_id='46a52585612a906c'; page_start=246; page_end=385; label='Chapter 4'}} | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:786/chat -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```
UI URL options: `?lang=English|Hinglish|Urdu|Hindi` (directions language) · `?tour=1` (start the arrow tour; `?tour=5` at step 5) · `?guide=1` (open Guide) · `?guide=0` (no welcome popup — screenshots) · `?session=<id>` · `?theme=dark`.
Headless-Chrome screenshots draw the sticky composer ~100 px lower than the page measures it, so tour arrows near the composer look misplaced there; check those in a real browser.

Book ids: `46a52585612a906c` = Muqaddima Seerat-ur-Rasool ﷺ, `c2fd1e0906c9c087` = Creation of Man.

Open PowerShell and start the app:

```powershell
cd D:\mufti-ai
.\start.ps1
```

If PowerShell blocks the script, use the direct command:

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 786 --no-access-log
```

Open [http://localhost:786](http://localhost:786). Port `0786` is written as `786` in commands. Press **Ctrl+C** in the server window to stop it.

## Ollama and local models

Keep Ollama running. The Windows Ollama app normally starts the service automatically. If it is not running, open a separate PowerShell window and run:

```powershell
ollama serve
```

Install the embedding model and your preferred local answer model:

```powershell
ollama pull bge-m3
ollama pull qwen3:1.7b
ollama pull gemma3:1b
ollama list
```

In **Models & fallback**, select an installed local model. **Gemini** uses Google's cloud API; **Gemma** runs locally through Ollama. A local model must be installed and Ollama must be running for the final fallback to answer.

## Add cloud providers

Edit the local environment file; keep API keys out of the chat and browser:

```powershell
notepad D:\mufti-ai\.env
```

Add only the keys for services you want to use:

```dotenv
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_gemini_key
```

Restart Mufti AI after changing keys. In **Models & fallback**, choose **Auto**, set model IDs that your accounts can access, and save. The default cloud order is **Anthropic → OpenAI → Gemini → Ollama**. You can change that order. A selected cloud provider is tried first, followed by the other configured clouds and finally Ollama. **Ollama only** keeps answer generation local.

Providers without keys are skipped. When a provider's quota is exhausted or it is unavailable, the app tries the next provider. Cloud mode sends your question, recent conversation context and selected PDF excerpts to configured providers as needed. Keys must have usable API credit/quota; entering a key does not guarantee access to every model.

## Run checks

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m pytest tests -q
```


## Model folder check after moving drives

On this machine Ollama uses `D:\ollama-models`. This folder now includes `bge-m3`, `qwen3:1.7b`, `gemma3:1b` and the existing Llama model. Keep D: connected. A working cloud key does not replace the local `bge-m3` search requirement.

```powershell
ollama list
Invoke-RestMethod http://localhost:786/health
Invoke-RestMethod http://localhost:786/settings/models
```

If the models disappear after changing `OLLAMA_MODELS`, check that Ollama is using the intended model folder before downloading them again. Start `ollama serve` only when the service is not already listening. Start Mufti AI in a second terminal using the commands above. Keep both services running while using the app.

## Expected answer times on this machine

This laptop has a 2 GB NVIDIA MX450, and the local model generates at roughly 1.6-3.0 tokens a
second. That is the whole story behind the timings:

| Question type | Typical time |
|---|---|
| Author, publisher, ISBN, first publication | about **1 second** (reviewed facts, no model generation) |
| A content question answered locally | **tens of seconds to a few minutes** |

A content question is not stuck at 60 seconds. The status line keeps naming the current step
and the elapsed time; let it run. Cloud models answer in seconds, but only with usable quota.

## Checking the search index

The book is searched through a staged child-segment index that sits beside the page index:

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m app.ingestion.segment_index status
```

It should report an `active` build with `embedding_model: bge-m3`. If `active` is `null`, search
falls back to whole pages and answers get noticeably worse. Rebuild it:

```powershell
.\.venv\Scripts\python.exe -m app.ingestion.segment_index build
.\.venv\Scripts\python.exe -m app.ingestion.segment_index validate --build-id <id>
.\.venv\Scripts\python.exe -m app.ingestion.segment_index activate --build-id <id>
```

Activate only when `validate` reports `ok: true`. `rollback` undoes an activation. A rebuild
takes a few minutes and reuses cached embeddings; it never touches the original PDF, the page
index, the reviewed book details or your saved conversations.

## Choosing a local model on a 2 GB GPU

Open **Models & fallback** and pick an installed local model. On this machine `qwen3:1.7b`
(1.4 GB) fits in the GPU and is the current setting. `llama3.2:3b` is 2.0 GB against a 2 GB
card, which made it both slower and measurably worse — it produced claims the source did not
support, which the app then rejected, so questions came back with no answer. `gemma3:1b` is the
fastest and the weakest.

## Diagnosing a question that returns no answer

Every real request writes a trace to `data/diagnostics/`. The newest file explains the outcome:

```powershell
cd D:\mufti-ai
Get-ChildItem data\diagnostics\*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

Inside it, `retrieval.candidate_scores` shows which pages were found, `evidence.windows` shows
what was sent to the model, and `verification.rejections` says why each claim was dropped.
`outcome.reason_code` distinguishes the cases that matter:

- `no_matching_passages` — the search found nothing above the relevance floor.
- `insufficient_coverage` — pages were found and read, but none directly answers the question.
- `unsupported_claims` — a draft was written but no claim survived source checking. The related
  passages shown are worth reading; the model's wording was not supportable.
- `provider_quota_exhausted` / `provider_unavailable` / `retrieval_unavailable` — a **service**
  problem, not a statement about the book. Check Ollama and your model settings.

## Checking your cloud quota

A configured key is not usable quota. The settings dialog says so honestly: "Key configured ·
not yet used", "Quota or rate limit reached", "Paused after failures". To test a key directly:

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -c "import asyncio,sys; sys.path.insert(0,'.'); from app.llm.providers import complete; print(asyncio.run(complete('gemini','gemini-2.5-flash',[{'role':'user','content':'hi'}])))"
```

An `HTTPStatusError` with 429 means the quota is exhausted; answers then come from the local
model, which is slower. That is a billing or plan limit, not a fault in the app.

## Long-running evaluation jobs

Measure retrieval (minutes), then answers (hours). Start these so they survive the terminal:

```powershell
cd D:\mufti-ai
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-u","-m","eval.run_benchmark","--retrieval","--holdout" -WindowStyle Hidden -RedirectStandardOutput "eval\retrieval.log" -RedirectStandardError "eval\retrieval.err"
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-u","-m","eval.run_benchmark","--answers","--holdout","--out","eval/benchmark-answers.json" -WindowStyle Hidden -RedirectStandardOutput "eval\answers.log" -RedirectStandardError "eval\answers.err"
```

To ask one question from the command line and see the retrieval detail:

```powershell
.\.venv\Scripts\python.exe -m eval.probe "Explain Gender Equality in detail" --retrieval-only
.\.venv\Scripts\python.exe -m eval.probe "Explain Gender Equality in detail"
```

To compare installed local models on the same questions without changing your saved settings:

```powershell
.\.venv\Scripts\python.exe -m eval.compare_local_models qwen3:1.7b llama3.2:3b -- ge-en-1 piety-en-1
```

## Finding the running server

The pid that launches uvicorn is not the pid that ends up listening, so look up the listener
rather than trusting a number written down earlier:

```powershell
Get-NetTCPConnection -LocalPort 786 -State Listen | Select-Object OwningProcess
```

## Commands added 2026-11-13

### Build the Book / Chapter / Section page-range tree

Run once per book, and again whenever the PDF is replaced. It reads the PDF outline only and
calls no model, so it finishes in seconds.

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m app.ingestion.book_tree
```

Expect `{"outline_entries": 310, "chapters": 9, "sections": 301, "problems": []}` for the
current book. A non-empty `problems` list means a page range failed validation; the tree is
still written, and the entries it names should be inspected before relying on them. A book
whose PDF has no outline reports `outline_entries: 0` and simply has no tree: everything else
keeps working.

The tree is written to `data\index\trees\<book_id>.json` and records the PDF's SHA-256, so a
replaced book is detectable.

### Ask one question end to end

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -m eval.probe "Explain Gender Equality in detail"
.\.venv\Scripts\python.exe -m eval.probe --retrieval-only "Explain Gender Equality in detail"
```

`--retrieval-only` skips every answering model call and finishes in seconds, which separates a
retrieval miss from a drafting or verification failure without waiting on a local model.

Add `--mode gemini` (or `anthropic`, `openai`, `ollama`) to run that one question against a
different provider **without changing `model-settings.json`**. The override lives only for
that process; the app itself always reads your saved preference.

### Measure retrieval

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -u -m eval.run_benchmark --retrieval --holdout --out eval\bench-ret.json
```

`--windows 8` sets the evidence windows per case. The shipping default is `evidence_windows`
in `app\core\config.py` (6, chosen for local latency); earlier measurements in this repo were
taken at 8, so pass `--windows 8` to compare against them like for like.

To measure the configuration without the page-tree route (the shipping default is off):

```powershell
$env:ENABLE_TREE_ROUTE = "false"
.\.venv\Scripts\python.exe -u -m eval.run_benchmark --retrieval --holdout --out eval\bench-ret-hybrid.json
Remove-Item Env:\ENABLE_TREE_ROUTE
```

Any setting in `app\core\config.py` can be overridden by an environment variable of the same
name in upper case, which is how `off_concept_factor` was swept.

### Measure the answer stage, resumably

```powershell
cd D:\mufti-ai
.\.venv\Scripts\python.exe -u -m eval.run_benchmark --answers --holdout --resume --out eval\benchmark-answers.json
```

**Always pass `--resume`.** Per-case results are written to `--out` after every case, and
`--resume` reads them back and runs only what is missing. Two earlier runs were lost outright
at 29/48 and 6/48 cases because this did not exist. On the local model a full pass is several
hours; add `--mode gemini` to run it against a cloud model in well under one.

Start long runs with `Start-Process` so they survive the shell that launched them:

```powershell
Start-Process -FilePath "D:\mufti-ai\.venv\Scripts\python.exe" `
  -ArgumentList '-u','-m','eval.run_benchmark','--answers','--holdout','--resume','--out','eval/benchmark-answers.json' `
  -WorkingDirectory "D:\mufti-ai" `
  -RedirectStandardOutput "D:\mufti-ai\eval\answers-run.log" `
  -RedirectStandardError  "D:\mufti-ai\eval\answers-run-error.log" -WindowStyle Hidden
```

### Find the real listener before trusting any recorded pid

```powershell
Get-NetTCPConnection -LocalPort 786 -State Listen | Select-Object LocalPort, OwningProcess
```

A launch pid is not the listener. On 2026-11-12 the launch pid was 5504 while the listener was
13628.

## If the D: drive disconnects

This project lives on an external SSD that dropped out repeatedly on 2026-11-13. Windows
logged 6,653 disk I/O errors in twenty minutes; the source PDF and every `.md` file became
unreadable, and the server died mid-request with `OSError: [Errno 22] Invalid argument: '.env'`.
None of that is an application fault and no amount of retrying in code fixes it.

Check whether the drive is actually healthy before debugging anything else:

```powershell
# Is a file really readable, or only listed? Get-ChildItem can list a file that cannot be read.
try { [System.IO.File]::OpenRead("D:\mufti-ai\.env").Close(); "OK" } catch { $_.Exception.InnerException.Message }

# How many I/O errors has Windows logged recently?
(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='disk'; StartTime=(Get-Date).AddMinutes(-20)}).Count
```

A healthy result is 0 to a handful. Thousands means reconnect the drive (reseat the cable)
before continuing. A full working backup taken during that outage is at `C:\mufti-ai-salvage`:
it contains the source, the venv, the active segment index and the book, and the test suite
passes from it unchanged, so it can be used directly if D: is unavailable.

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

## Explanation mode commands (2026-11-16)

```powershell
cd D:\mufti-ai
# Ollama must run even in cloud mode: the bge-m3 search embeddings are local.
curl.exe -s --max-time 5 http://127.0.0.1:11434/api/tags
# Start the app (hidden). Find the real listener afterwards; never trust the launch pid.
Start-Process -FilePath .\.venv\Scripts\python.exe -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','786','--no-access-log' -WindowStyle Hidden -RedirectStandardOutput server.log -RedirectStandardError server-error.log
Get-NetTCPConnection -LocalPort 786 -State Listen

# One live question through the full pipeline (does not change model-settings.json):
.\.venv\Scripts\python.exe -u -m eval.probe "Explain Gender Equality in detail" --mode gemini

# Answer-stage benchmark over all 48 reviewed cases. STOP THE SERVER FIRST (shared 2 GB GPU).
.\.venv\Scripts\python.exe -u -m eval.explain_eval --mode gemini --out eval\explain-eval-gemini.json --delay 8
# Resume after an interruption, or rerun chosen cases:
.\.venv\Scripts\python.exe -u -m eval.explain_eval --mode gemini --resume --out eval\explain-eval-gemini.json
.\.venv\Scripts\python.exe -u -m eval.explain_eval --mode gemini --ids ge-ur-1,cm-en-3

# Offline suite (expect 203 passed) and UI syntax check
.\.venv\Scripts\python.exe -m pytest tests -q
node --check frontend\app.js
```

**Gemini free tier is per model and small.** Measured 2026-11-16: `gemini-2.5-flash` allows
20 requests/day (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`). Each question costs two
calls (answer + audit). The router skips a model that reported a quota until its retry delay
and moves through `gemini_alternates` in `config.yaml`; the audit runs first on
`gemini-3.1-flash-lite`. Primary answering model: `gemini-3.5-flash`. Check quotas with a
direct one-token call before concluding a provider is down.

Switch answer style: `answer_mode` in `app/core/config.py` — `explain` (default) or `strict`.

## If D: is unstable: run Ollama from the C: model store (2026-11-16)
```powershell
Get-Process ollama* | Stop-Process -Force
$env:OLLAMA_MODELS="$env:USERPROFILE\.ollama\models"   # this session only
Start-Process ollama -ArgumentList serve -WindowStyle Hidden
```
Add a book: copy the PDF to data\books, stop the server, then
`.\.venv\Scripts\python.exe -m app.ingestion.indexer` ->
`python -m app.ingestion.segment_index build` -> `validate --build-id <id>` -> `activate --build-id <id>` ->
`python -m app.ingestion.book_tree`, and add reviewed metadata in data\book-metadata\<book_id>.json.
