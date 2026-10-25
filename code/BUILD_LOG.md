# Build Log — TogetherFund VC Agents

A record of what was added to this repo, the errors hit along the way, and
the current state. Written for two audiences: future-me debugging this
again, and an interviewer asking "walk me through how you built this."

---

## What we built

**1. Root `README.md`** — architecture (ASCII diagrams for both agents),
design decisions framed as engineering tradeoffs (zero-framework, Groq,
Tavily, SQLite, APScheduler), run instructions, eval results.

**2. Eval harness for the DD Agent** (`code/Due-Dilligence-Agent/eval/`)
- `golden_set.json` — 5 real AI companies (Perplexity, Groq, Mistral,
  Together AI, Sarvam) with ground-truth founder/funding/product keywords.
- `run_eval.py` — runs the live agent on each company, scores field-level
  accuracy, appends timestamped runs to `results.json`, exits non-zero if
  overall accuracy drops below 0.75 (the CI gate threshold).

**3. Slack alerts** (`code/Portfolio-health-monitor/app/alerts.py`) — wired
into `monitor.py`'s `run_company_analysis`. Fires only on a flip *into* red
status (checks the previous snapshot so it doesn't re-alert every run).
Skips silently if `SLACK_WEBHOOK_URL` is unset — never breaks the pipeline.

**4. CI gate** (`.github/workflows/eval.yml`) — runs `eval/run_eval.py` on
every push/PR to `main`, uploads `results.json` as a build artifact. Same
pattern as the FintelRAG project's faithfulness gate.

**5. Structured logging** (`logging_utils.py` in both agents) — one
`log_event(tool, input, output_len, latency_ms, **extra)` function, stdlib
only (`json` + `time`), wired into every Tavily call, every DDG call, and
both Groq calls. Writes to `logs/dd_agent.jsonl` and
`logs/portfolio_monitor.jsonl`.

**6. Repo hygiene cleanup**
- Removed the hardcoded `C:\Users\kusha\...` venv path from `SUBMISSION.md`.
- Removed the "what I'd do with two more weeks" section (signals
  incompleteness on a resume artifact).
- Fixed stale `cd dd-agent` / `cd portfolio-health-monitor` paths in
  `SUBMISSION.md` that didn't match the actual `code/Due-Dilligence-Agent`
  / `code/Portfolio-health-monitor` layout.
- Added root-level `.env.example`; fixed `Portfolio-health-monitor`'s
  `.env.example`, which wrongly listed an unused `TAVILY_API_KEY`.

**7. Model configurability** — both agents now read the Groq model from a
`GROQ_MODEL` env var (default `openai/gpt-oss-120b`) instead of a hardcoded
string in 3+ call sites. See "Errors" below for why this mattered twice in
one session.

---

## Errors faced (in order)

### 1. GitHub push protection — leaked Groq API key
**Symptom:** `git push` rejected with `GH013: Repository rule violations
found ... Push cannot contain secrets`, pointing at a real Groq key
committed into `code/Portfolio-health-monitor/.env.example`.

**Root cause:** a real key got typed into the `.env.example` template file
instead of the real `.env` file, then committed.

**Fix:** the bad commit (`d43ef82`) had to be rewritten, not just
superseded — GitHub scans the full history being pushed, so a later commit
that blanks the file doesn't help; the secret is still reachable in an
earlier commit object. Fixed via `git reset --soft` back to the last known
clean commit (`origin/main`) and recommitting everything fresh as one
commit, so no commit object containing the secret was ever part of the
pushed history.

**Lesson:** `.env.example` should never be opened with "paste my key here"
muscle memory — a key-rotation discipline afterward is the only real safety
net once a secret has touched a terminal or an editor buffer at all. The
key was rotated at console.groq.com after this.

### 2. Nested/misplaced files from manual zip extraction
**Symptom:** `git status` showed a duplicated
`TogetherFund-VC-Agents-changes/TogetherFund-VC-Agents-changes/...` folder,
and separately `README.md` / `SUBMISSION.md` / `.github/` landed inside
`code/` instead of the repo root.

**Root cause:** the provided zip was extracted from inside `code/` instead
of the repo root, and extracted twice.

**Fix:** `Remove-Item -Recurse -Force` on the stray folder, `Move-Item` to
relocate the misplaced root-level files back out of `code/`.

### 3. `llama-3.3-70b-versatile` — `model_not_found` (404)
**Symptom:** `eval/run_eval.py` failed on step 1 with
`The model 'llama-3.3-70b-versatile' does not exist or you do not have
access to it`.

**Root cause:** Groq deprecated and decommissioned this model ID on this
account. (Public docs were inconsistent at the time of debugging — some
sources still listed it as current, others confirmed decommission — so the
account's actual live model list was the only reliable source of truth.)

**First fix attempt:** swapped to `llama-3.1-8b-instant` — also 404'd.

### 4. `llama-3.1-8b-instant` — `model_not_found` (404), same error
**Symptom:** identical error, different model name.

**Root cause:** querying `GET https://api.groq.com/openai/v1/models`
directly with the account's real key showed the **entire Llama model
family is gone from this account's catalog** — not a single deprecated ID,
but the whole lineup. Available models were OpenAI's `gpt-oss-20b` /
`gpt-oss-120b`, Alibaba's `qwen/qwen3.8-27b`, `allam-2-7b`, Whisper, and a
couple of speech/guard models.

**Real fix:** switched both agents to `openai/gpt-oss-120b` (the only
available model with `structured_outputs` + `json_mode` support, which the
JSON-synthesis prompts in both agents depend on), **and** made the model
name configurable via a `GROQ_MODEL` env var instead of hardcoded, so a
third Groq catalog change doesn't require another code hunt — just a
`.env` edit.

**Lesson:** when the same class of error survives a plausible fix, stop
guessing from search results and query the provider's live endpoint for
that specific account/key. Two wrong guesses in a row was the signal to
do that.

### 5. PowerShell `curl` alias friction
**Symptom:** `curl ... -H "Authorization: Bearer $key"` failed with
`Cannot bind parameter 'Headers'` — PowerShell aliases `curl` to
`Invoke-WebRequest`, which expects `-Headers` as a hashtable, not a raw
string.

**Fix:** `Invoke-RestMethod -Uri ... -Headers @{ Authorization = "Bearer
$env:GROQ_API_KEY" }`, or `curl.exe` explicitly to bypass the alias.

### 6. Eval golden-set false negative — Sarvam AI founder field
**Symptom:** eval scored 93.3% overall; the one miss was Sarvam AI's
founder field.

**Root cause:** Sarvam AI has two co-founders (Vivek Raghavan, Pratyush
Kumar). `golden_set.json` encoded only one name as ground truth; the
agent's live web research surfaced the other, equally correct, co-founder.
This is a limitation of single-keyword string matching, not a confirmed
factual error in the agent's output.

**Status:** left as a documented known limitation rather than "fixed," since
it's a more honest and more interview-useful story than silently loosening
the eval until it passes — and it's a real illustration of why RAGAS-style
LLM-judge evaluation exists instead of keyword matching for anything beyond
a quick baseline (see Day 9 of the AI engineer roadmap in this project).

---

## Current state / what we achieved

- Both agents run end-to-end against the live Groq + Tavily APIs.
- `python -m eval.run_eval` passes: **93.3% overall memo accuracy**
  (founder 80%, funding 100%, product 100%) against a 5-company golden set,
  above the 0.75 CI threshold.
- CI (`.github/workflows/eval.yml`) runs the same eval on every push to
  `main` and will fail the build below that threshold.
- Structured JSONL logs recorded for every Tavily/DDG/Groq call
  (`logs/dd_agent.jsonl`, `logs/portfolio_monitor.jsonl`).
- Slack alerting wired in (untested live — needs a real
  `SLACK_WEBHOOK_URL` and a company actually flipping to red to confirm
  end-to-end; logic has been reviewed but not exercised against a live
  webhook as of this log).
- No secrets present in current git history; leaked key rotated.
- Model selection is now env-configurable (`GROQ_MODEL`), decoupling the
  codebase from Groq's model lifecycle.

## Not yet done / open items

- Slack alert path (`notify_if_red`) hasn't been exercised against a real
  webhook end-to-end — worth a manual test before relying on it.
- GitHub repo description/topics/website (repo settings, not files —
  needs to be set manually in the GitHub UI).
- Sarvam AI founder-field eval false negative (see Error 6) — left
  documented rather than patched; revisit if a stricter golden set is
  wanted later.