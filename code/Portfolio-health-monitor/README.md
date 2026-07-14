# Together Fund — Portfolio Health Monitor

AI-powered weekly signal monitor for Together Fund's portfolio companies.
Collects headcount trends, news signals, and job postings → Groq/Llama synthesises into red/yellow/green health status with reasoning.

---

## Setup

### 1. Clone / copy the project folder
```
portfolio-health-monitor/
├── app/
│   ├── __init__.py
│   ├── monitor.py
│   ├── database.py
│   ├── scheduler.py
│   └── models.py
├── data/
│   └── companies.json
├── dashboard.py
├── .env
└── requirements.txt
```

### 2. Activate your virtual environment
```bash
# Windows
C:\Users\kusha\OneDrive\Desktop\war\venv\Scripts\activate
```

### 3. Install dependencies — one by one (Windows/Anaconda safe order)
```bash
pip install groq==0.9.0
pip install duckduckgo-search==5.3.1b1
pip install streamlit==1.35.0
pip install pydantic==2.7.4
pip install apscheduler==3.10.4
pip install python-dotenv==1.0.1
pip install plotly==5.22.0
pip install pandas==2.2.2
```

> ⚠️ **Do NOT install `duckduckgo-search` v6+** — it pulls in `pyreqwest-impersonate`
> which requires Rust/Cargo to compile on Windows and will fail.
> Always use `==5.3.1b1`.

### 4. Create your `.env` file
```env
GROQ_API_KEY=gsk_xxxxx
```
Get a free key at https://console.groq.com

### 5. Run
```bash
streamlit run dashboard.py
```
Opens at `http://localhost:8501`

---

## Architecture

```
dashboard.py (Streamlit UI)
    ↓ triggers
app/monitor.py (agent loop: collect signals → Groq/Llama analysis)
    ↓ persists
app/database.py (SQLite — one row per company per scan)
    ↑ scheduled by
app/scheduler.py (APScheduler — Mondays 07:00 AM)
```

### Agent loop per company (monitor.py):
1. **STEP 1** — Headcount delta from 6-month seed history
2. **STEP 2** — DuckDuckGo news search (last 30 days)
3. **STEP 3** — DuckDuckGo job postings search (fallback to broader query if < 2 results)
4. **STEP 4** — GitHub activity proxy (only if company has a github handle)
5. **GROQ** — Single structured call synthesising all signals → `{status, headline, reasoning, signals_used, recommended_action, confidence}`

All steps stream live to the Streamlit log console as they run.

---

## Known Issues & Fixes

| Error | Fix |
|-------|-----|
| `Failed to build pyreqwest-impersonate` (Cargo/Rust error) | Use `duckduckgo-search==5.3.1b1` not v6+ |
| `ModuleNotFoundError: No module named 'plotly'` | `pip install plotly==5.22.0 pandas==2.2.2` |
| `ModuleNotFoundError: No module named 'apscheduler'` | `pip install apscheduler==3.10.4` |
| Sidebar not visible / collapse arrow missing | Remove `header { visibility: hidden; }` from CSS in dashboard.py — keep only `#MainMenu` and `footer` hidden |
| Sidebar collapses on every reload | Set `initial_sidebar_state="expanded"` in `st.set_page_config` |

---

## Why no LangChain / LangGraph?

Raw Groq API + manual loop = full control, zero abstraction overhead, and
cleaner error surfaces. The agent behaviour is ~40 lines in `monitor.py` —
readable in one sitting. LangGraph adds value for multi-agent handoffs with
10+ nodes; a focused 4-step signal loop doesn't need it.

## Data note

Headcount history is seeded synthetic data (6-month window per company) in
`data/companies.json`. News and job signals are live DuckDuckGo searches.
In production: replace headcount seed with a LinkedIn API partner (Proxycurl)
or founder-reported quarterly updates.