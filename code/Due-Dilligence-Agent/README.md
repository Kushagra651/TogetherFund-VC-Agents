# Due Diligence Research Agent
Autonomous multi-step research agent that investigates a startup and produces a structured DD memo for Together Fund partners.

## What it does
Takes a company name, one-line description, and founder LinkedIn URL → runs 5 autonomous search steps → produces a structured 2-page due diligence memo with market, competition, founder, traction, red flags, verdict, and confidence score. Every reasoning step is visible live in the UI.

## Architecture
```
app.py (Streamlit frontend)
└── agent/core.py        ← agentic loop + Groq LLM calls
      ├── agent/tools.py ← Tavily search + disk cache
      ├── agent/prompts.py
      └── agent/memo_schema.py (Pydantic)
```

## Why no LangChain/LangGraph
Built from scratch to demonstrate agentic primitives directly — a loop, conditional branching on observed results, and context accumulation across steps. Framework overhead hides reasoning; every line of `core.py` is readable and debuggable.

## Prerequisites
- Python 3.11
- Anaconda (recommended)
- Groq API key → [console.groq.com](https://console.groq.com) (free)
- Tavily API key → [app.tavily.com](https://app.tavily.com) (free, 1000 searches/month)

## Setup

### 1. Create and activate virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 2. Install dependencies one by one (Windows/Anaconda — avoids Rust/cmake build errors)
```bash
pip install duckduckgo-search==5.3.1b1
pip install streamlit
pip install pydantic
pip install python-dotenv
pip install groq
pip install tavily-python
```

### 3. Configure environment
Create a `.env` file in the project root:
```
GROQ_API_KEY=gsk_your_key_here
TAVILY_API_KEY=tvly_your_key_here
```
No quotes around the values.

### 4. Run
```bash
streamlit run app.py
```

## Usage
1. Enter company name (e.g. `Sarvam AI`)
2. Enter one-line description (e.g. `Indian LLM for regional languages`)
3. Enter founder LinkedIn URL (e.g. `https://www.linkedin.com/in/vivekraghavan/`)
4. Click **Run Due Diligence**
5. Watch the agent reason live on the left → memo appears on the right

## Project Structure
```
Due-Dilligence-Agent/
├── .env                    # API keys (never commit)
├── .env.example
├── requirements.txt
├── README.md
├── app.py                  # Streamlit UI
├── agent/
│   ├── __init__.py
│   ├── core.py             # Agentic loop
│   ├── tools.py            # Tavily search + cache
│   ├── prompts.py          # All LLM prompt templates
│   └── memo_schema.py      # Pydantic DDMemo model
├── cache/                  # Search result cache (auto-created)
└── sessions/               # Completed DD runs as JSON (auto-created)
```

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: groq` | `pip install groq` |
| `ModuleNotFoundError: dotenv` | `pip install python-dotenv` |
| `ModuleNotFoundError: streamlit` | `pip install streamlit` |
| `HTTP Error 401` on search | Add `load_dotenv()` to top of `tools.py`; check `.env` has no quotes around keys |
| `model_decommissioned` from Groq | Change model to `llama-3.3-70b-versatile` in `core.py` |
| DDG `202 Ratelimit` | Switched to Tavily — DDG no longer used as primary search |
| cmake/Rust build error on Windows | Use `duckduckgo-search==5.3.1b1` (pure Python, no Rust needed) |
| Streamlit not found | Run `pip install streamlit` inside your activated venv |

## Notes
- Search results cached in `cache/` as JSON — re-runs are instant and never hit the network
- If a cached result is a failure, it is auto-deleted and retried fresh
- Sessions saved to `sessions/` per run — useful for showing run history in demo
- Model: `llama-3.3-70b-versatile` on Groq free tier
- Search: Tavily API (purpose-built for LLM agents, no IP blocking)