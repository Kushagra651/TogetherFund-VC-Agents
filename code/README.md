# TogetherFund VC Agents

Two zero-framework AI agents for VC workflow automation, built for Together
Fund (an operator-led AI-first VC in India) as a technical intern assignment:
a **Due Diligence Research Agent** that turns a company name into a
structured investment memo, and a **Portfolio Health Monitor** that runs a
weekly, unattended red/yellow/green check across the portfolio and alerts on
distress. Both agentic loops are hand-written — no LangChain, no LangGraph —
so every decision the agent makes is a line of Python you can point to.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DD RESEARCH AGENT                           │
│                                                                       │
│  Streamlit UI (app.py)                                               │
│       │  company + description + founder LinkedIn                   │
│       ▼                                                               │
│  core.py — agentic loop (5 steps)                                    │
│       │                                                               │
│       │  for step in 1..5:                                           │
│       │    ┌──────────────────────────────────────────────┐         │
│       │    │ Groq llama-3.3-70b → next search query        │         │
│       │    │          ▼                                     │         │
│       │    │ tools.py → Tavily search (disk-cached by MD5)  │         │
│       │    └──────────────────────────────────────────────┘         │
│       │  (step 1→competitors, 2→funding, 3→founder, 4→TAM, 5→news)  │
│       ▼                                                               │
│  synthesis: Groq → structured JSON → Pydantic DDMemo                 │
│       │                                                               │
│       ├──► sessions/*.json   (full run persisted)                    │
│       └──► Streamlit memo panel                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      PORTFOLIO HEALTH MONITOR                        │
│                                                                       │
│  scheduler.py — APScheduler cron (Mon 07:00, no human trigger)       │
│   + Streamlit dashboard "Run Analysis" button (manual trigger)       │
│       │                                                               │
│       ▼                                                               │
│  monitor.py — per company in companies.json:                         │
│       │  1. collect_signals(): headcount Δ, DDG news, DDG job posts, │
│       │                        GitHub activity proxy                 │
│       │  2. analyze_with_claude(): single Groq call → structured     │
│       │                        HealthSummary (status/reasoning/      │
│       │                        confidence)                           │
│       │  3. save_report() → SQLite (data/portfolio.db)               │
│       │  4. notify_if_red() → Slack webhook, only on a RED flip      │
│       ▼                                                               │
│  dashboard.py — red/yellow/green cards, "why this status?", trends   │
└─────────────────────────────────────────────────────────────────────┘

Both agents write structured JSONL to logs/ on every tool call
(search, LLM) — see "Observability" below.
```

---

## Key design decisions

**Zero-framework, by choice.** Both agentic loops are custom, ~40 lines
each (`core.py`, `monitor.py`). LangGraph or LangChain would abstract that
loop into framework config — fine at larger scale, but overkill for a loop
this size, and it means I can walk through the exact control flow line by
line instead of pointing at a library.

**Groq over Anthropic/OpenAI for the agent loop.** `llama-3.3-70b-versatile`
on Groq's free tier is fast enough for a live demo with no cost barrier, and
the client is OpenAI-compatible — swapping providers is a one-line change if
latency or quality ever requires it.

**Tavily over DuckDuckGo for the DD agent.** DDG rate-limits aggressively at
the IP level under repeated demo runs. Tavily is purpose-built for LLM
agents: structured JSON results, no blocking, 1,000 free searches/month.
(The Portfolio Monitor still uses DDG — its search volume is much lower and
weekly-cron-paced, so the rate limit risk doesn't apply the same way.)

**SQLite for portfolio snapshots.** Trend analysis only needs point-in-time
reads with no concurrent writers — a single-file embedded DB avoids standing
up Postgres for a dataset this size, while still giving real historical
queries (`get_company_history`).

**APScheduler for the weekly cron.** Runs the monitor unattended inside the
same process as the dashboard — no separate cron daemon or external
scheduler needed for a weekly cadence at this scale.

---

## How to run

Both tools share one virtual environment; dependencies don't conflict.

```bash
# from the repo root
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r code/Due-Dilligence-Agent/requirements.txt
pip install -r code/Portfolio-health-monitor/requirements.txt
```

### Tool 1 — DD Research Agent

```bash
cd code/Due-Dilligence-Agent
cp .env.example .env            # add GROQ_API_KEY and TAVILY_API_KEY
streamlit run app.py            # http://localhost:8501
```

Enter a company name, one-line description, and founder LinkedIn URL. The
agent researches in 5 steps (competitors → funding → founder → TAM →
news/red-flags), streaming its findings live, then synthesizes a structured
memo.

### Tool 2 — Portfolio Health Monitor

```bash
cd code/Portfolio-health-monitor
cp .env.example .env            # add GROQ_API_KEY (SLACK_WEBHOOK_URL optional)
streamlit run dashboard.py      # http://localhost:8501
```

Click **Run Analysis** to collect signals and score all 10 portfolio
companies, or let the Monday 07:00 cron do it unattended. Red/yellow/green
cards show the verdict; "Why this status?" shows the LLM's reasoning;
"Historical snapshots" shows the trend.

### API keys needed

| Key | Where to get it | Used by |
|---|---|---|
| `GROQ_API_KEY` | console.groq.com (free) | Both tools |
| `TAVILY_API_KEY` | app.tavily.com (free, 1,000/month) | DD Agent only |
| `SLACK_WEBHOOK_URL` | Slack → Incoming Webhooks app (optional) | Portfolio Monitor only — skipped silently if unset |

---

## Eval

The DD agent has a golden set of 5 real companies with known ground-truth
fields (founder, funding stage, product category). `eval/run_eval.py` runs
the live agent against each and scores field-level accuracy.

```bash
cd code/Due-Dilligence-Agent
python -m eval.run_eval
```

CI (`.github/workflows/eval.yml`) runs this on every push to `main` and
fails the build if overall memo accuracy drops below 0.75.

**Latest run (2026-10-25):**

| Field | Accuracy |
|---|---|
| Founder | 80% |
| Funding | 100% |
| Product | 100% |
| **Overall memo accuracy** | **93.3%** |

4/5 companies scored perfectly across all three fields. The one miss
(Sarvam AI's founder field) is a multi-co-founder edge case: Sarvam has two
co-founders (Vivek Raghavan, Pratyush Kumar), and the agent's memo named a
different one than the single name encoded as ground truth in
`eval/golden_set.json`. That's a known limitation of single-keyword string
matching, not a confirmed factual error in the agent's output — the kind of
gap RAGAS-style LLM-judge evaluation (vs. keyword matching) is built to
avoid.

Same pattern used on [FintelRAG](https://github.com/Kushagra651/FintelRAG)'s
CI gate (faithfulness < 0.80 fails the PR) — consistent eval-driven
reliability thinking across projects.

---

## Observability

Every tool call (Tavily search, DDG search, Groq call, cache hit/miss) is
logged as one structured JSON line via a single `log_event(tool, input,
output_len, latency_ms, ...)` function — no external dependency, just
`json` + `time`.

```
logs/dd_agent.jsonl
logs/portfolio_monitor.jsonl
```

---

## Repo layout

```
TogetherFund-VC-Agents/
├── README.md
├── SUBMISSION.md
├── .env.example
├── code/
│   ├── Due-Dilligence-Agent/
│   │   ├── app.py, agent/ (core.py, tools.py, prompts.py, memo_schema.py,
│   │   │   logging_utils.py)
│   │   └── eval/ (golden_set.json, run_eval.py, results.json)
│   └── Portfolio-health-monitor/
│       ├── dashboard.py, main.py
│       └── app/ (monitor.py, database.py, models.py, scheduler.py,
│           alerts.py, logging_utils.py)
├── logs/ (dd_agent.jsonl, portfolio_monitor.jsonl)
└── .github/workflows/eval.yml
```