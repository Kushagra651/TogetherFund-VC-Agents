# Together Fund — Technical Intern Assignment
**Kushagra** | July 2026

---

## What's in this submission

```
submission/
├── SUBMISSION.md                        ← you are here
│
├── dd-agent/                            ← Tool 1: Due Diligence Research Agent
│   ├── app.py                           (Streamlit frontend)
│   ├── core.py                          (agentic loop)
│   ├── tools.py                         (Tavily search + disk cache)
│   ├── prompts.py                       (LLM prompt templates)
│   ├── memo_schema.py                   (Pydantic DDMemo model)
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
├── portfolio-health-monitor/            ← Tool 2: Portfolio Health Monitor
│   ├── dashboard.py                     (Streamlit frontend)
│   ├── app/
│   │   ├── monitor.py                   (agent loop + Groq analysis)
│   │   ├── database.py                  (SQLite read/write)
│   │   ├── models.py                    (Pydantic schemas)
│   │   └── scheduler.py                 (APScheduler weekly cron)
│   ├── data/
│   │   └── companies.json               (10 Together Fund portfolio companies)
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
└── docs/
    ├── Ideation_Kushagra.pdf            ← Part 1: 6 ideas + prioritisation
    ├── DD_Agent_Writeup.pdf             ← Part 2a: Tool 1 technical writeup
    └── Portfolio_Monitor_Writeup.pdf    ← Part 2b: Tool 2 technical writeup
```

---

## How to run

Both tools share the same virtual environment. All dependencies are
conflict-free.

### Setup (once)

```bash
# activate your venv
C:\Users\kusha\OneDrive\Desktop\war\venv\Scripts\activate

# Tool 1 dependencies
cd dd-agent
pip install -r requirements.txt

# Tool 2 dependencies
cd ../portfolio-health-monitor
pip install -r requirements.txt
```

### Tool 1 — DD Research Agent

```bash
cd dd-agent
cp .env.example .env        # add GROQ_API_KEY and TAVILY_API_KEY
streamlit run app.py
# opens at http://localhost:8501
```

**What to do:** Type a company name, one-line description, and founder
LinkedIn URL → hit Run → watch the agent research in real time on the left,
read the structured memo on the right.

**Demo company used:** Sarvam AI

---

### Tool 2 — Portfolio Health Monitor

```bash
cd portfolio-health-monitor
cp .env.example .env        # add GROQ_API_KEY
streamlit run dashboard.py
# opens at http://localhost:8501
```

**What to do:** Click **Run Analysis** in the sidebar → watch the live log
stream per company → read red/yellow/green cards → click "Why this status?"
on any card to see the LLM's reasoning → click "Historical snapshots" to see
trend data.

---

## API keys needed

| Key | Where to get it | Used by |
|-----|----------------|---------|
| `GROQ_API_KEY` | console.groq.com (free) | Both tools |
| `TAVILY_API_KEY` | app.tavily.com (free, 1000/month) | DD Agent only |

---

## Key decisions worth knowing before the interview

**Why Groq over Anthropic:** Groq's free tier with llama-3.3-70b-versatile
is fast enough for a live demo and has no cost barrier. The client is
OpenAI-compatible — swapping to Claude requires changing one line.

**Why Tavily over DuckDuckGo (DD Agent):** DDG rate-limits aggressively at
the IP level during repeated demo runs. Tavily is purpose-built for LLM
agents — structured results, no blocking, 1000 free searches/month.

**Why duckduckgo-search is pinned to 5.3.1b1 (Portfolio Monitor):** v6+
introduced pyreqwest-impersonate which requires Rust/Cargo to compile on
Windows. Pinned to the last version that installs cleanly via pip.

**Why no LangChain/LangGraph:** Both tools implement their own agentic loops
from scratch (~40 lines each). LangGraph adds abstraction overhead for a
loop simple enough to read in one sitting. The agent behaviour is in the
code, not in a framework config file.

**Why Streamlit over React:** Eliminates a separate frontend build step, SSE
streaming setup, and npm dependency chain. The live log console and Plotly
charts cover everything needed for a compelling demo.

---

## What I'd do with two more weeks

**DD Agent:** Replace Tavily with Crunchbase API for richer funding data.
Add PostgreSQL session store so the firm builds a cumulative research library.
Wire into email/form intake so pitches trigger DD runs automatically.

**Portfolio Monitor:** Proxycurl for real LinkedIn headcount data. Slack
webhook for automatic red-status alerts. Expand from 10 seed companies to
all 59 Together Fund portfolio companies (no code change — just additions to
companies.json).

---

*Both tools are independently runnable. Each has its own README with a
known-issues table covering every install error encountered during the build.*