# """
# Portfolio Health Monitor — Core Agent
# Collects multi-source signals per company, then runs a single structured
# Claude call to interpret them holistically. Not LangChain — raw API calls,
# full control, full visibility.
# """
# import os
# import time
# import json
# import logging
# from datetime import datetime
# from typing import Generator
# from duckduckgo_search import DDGS
# import anthropic
# from app.models import SignalSnapshot, HealthSummary
# from app.database import save_report, has_recent_data

# logger = logging.getLogger(__name__)
# client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# # ── Signal Collection ──────────────────────────────────────────────────────────

# def _search(query: str, max_results: int = 5) -> list[dict]:
#     """DuckDuckGo search with graceful rate-limit handling."""
#     try:
#         time.sleep(1.2)  # avoid DDG rate limits
#         with DDGS() as ddgs:
#             return list(ddgs.text(query, max_results=max_results))
#     except Exception as e:
#         logger.warning(f"Search failed for '{query}': {e}")
#         return []


# def collect_signals(company: dict, log_cb=None) -> SignalSnapshot:
#     """
#     Agentic signal collection loop. Each step informs the next.
#     log_cb: optional callable(str) for streaming log lines to UI.
#     """
#     def log(msg: str):
#         logger.info(msg)
#         if log_cb:
#             log_cb(msg)

#     name = company["name"]
#     history = company["headcount_history"]
#     current_hc = history[-1]
#     prev_hc = history[-2] if len(history) >= 2 else current_hc
#     delta_pct = round(((current_hc - prev_hc) / prev_hc) * 100, 1) if prev_hc else 0

#     log(f"[STEP 1] Collecting headcount signal for {name}...")
#     log(f"[STEP 1] Headcount: {prev_hc} → {current_hc} ({delta_pct:+.1f}%)")

#     log(f"[STEP 2] Searching recent news for {name}...")
#     news_results = _search(f'"{name}" news 2025', max_results=5)
#     headlines = [r.get("title", "") for r in news_results if r.get("title")]
#     log(f"[STEP 2] Found {len(headlines)} news mentions: {headlines[:2]}")

#     log(f"[STEP 3] Searching job postings for {name}...")
#     job_results = _search(f'"{name}" hiring jobs 2025 site:linkedin.com OR site:greenhouse.io OR site:lever.co', max_results=6)
#     # Also try a broader search if narrow one returns nothing
#     if len(job_results) < 2:
#         job_results = _search(f'"{name}" is hiring 2025', max_results=5)
#     job_titles = [r.get("title", "") for r in job_results if r.get("title")]
#     log(f"[STEP 3] Found {len(job_titles)} job posting signals")

#     # Step 4: GitHub activity if available
#     github_commits = None
#     if company.get("github"):
#         log(f"[STEP 4] Searching GitHub activity for {company['github']}...")
#         gh_results = _search(f'site:github.com/{company["github"]} commits 2025', max_results=3)
#         github_commits = len(gh_results) * 3  # rough proxy
#         log(f"[STEP 4] GitHub activity proxy score: {github_commits}")
#     else:
#         log(f"[STEP 4] No GitHub handle — skipping open-source activity check")

#     snapshot = SignalSnapshot(
#         company_name=name,
#         timestamp=datetime.utcnow().isoformat(),
#         headcount_current=current_hc,
#         headcount_previous=prev_hc,
#         headcount_delta_pct=delta_pct,
#         news_count=len(headlines),
#         news_headlines=headlines[:5],
#         job_postings_count=len(job_titles),
#         job_titles_sample=job_titles[:5],
#         github_commits_week=github_commits,
#     )
#     log(f"[STEP 4] Signal collection complete ✓")
#     return snapshot


# # ── Claude Analysis ────────────────────────────────────────────────────────────

# def analyze_with_claude(company: dict, snapshot: SignalSnapshot, log_cb=None) -> HealthSummary:
#     """
#     Single Claude call with all signals. Returns structured HealthSummary.
#     Reasoning is extracted directly from the response — no hidden chain-of-thought.
#     """
#     def log(msg: str):
#         logger.info(msg)
#         if log_cb:
#             log_cb(msg)

#     log(f"[CLAUDE] Synthesising signals for {company['name']}...")

#     prompt = f"""You are a portfolio health analyst for Together Fund, an AI-first VC in India.
# Analyse the following signals for portfolio company "{company['name']}" ({company['sector']}, founded {company['founded']}, last funding: {company['last_funding']}).

# SIGNALS THIS WEEK:
# - Headcount: {snapshot.headcount_previous} → {snapshot.headcount_current} ({snapshot.headcount_delta_pct:+.1f}%)
# - News mentions (last 30 days): {snapshot.news_count}
# - News headlines: {json.dumps(snapshot.news_headlines)}
# - Job postings found: {snapshot.job_postings_count}
# - Job titles sample: {json.dumps(snapshot.job_titles_sample)}
# - GitHub activity proxy: {snapshot.github_commits_week if snapshot.github_commits_week is not None else "N/A (not open source)"}
# - Headcount trend (last 6 months): {company['headcount_history']}

# TASK: Provide a structured health assessment. Think step by step before concluding.
# Consider: Is headcount growth healthy or declining? Is hiring aggressive (growth signal) or absent (stagnation)? Are there news signals of traction or distress? How does this compare to stage and sector norms?

# Respond ONLY with valid JSON matching this schema exactly:
# {{
#   "status": "green" | "yellow" | "red",
#   "headline": "one crisp sentence verdict under 20 words",
#   "reasoning": "2-4 sentence analytical reasoning citing specific signals",
#   "signals_used": ["list of 2-4 key signals that drove your verdict"],
#   "recommended_action": "one concrete action for the partner",
#   "confidence": "high" | "medium" | "low"
# }}"""

#     try:
#         response = client.messages.create(
#             model="claude-sonnet-4-6",
#             max_tokens=600,
#             messages=[{"role": "user", "content": prompt}]
#         )
#         raw = response.content[0].text.strip()
#         # Strip markdown fences if present
#         if raw.startswith("```"):
#             raw = raw.split("```")[1]
#             if raw.startswith("json"):
#                 raw = raw[4:]
#         data = json.loads(raw.strip())
#         log(f"[CLAUDE] Status: {data['status'].upper()} — {data['headline']}")
#         return HealthSummary(
#             company_name=company["name"],
#             timestamp=datetime.utcnow().isoformat(),
#             **data
#         )
#     except Exception as e:
#         logger.error(f"Claude analysis failed for {company['name']}: {e}")
#         return HealthSummary(
#             company_name=company["name"],
#             status="yellow",
#             headline="Analysis unavailable — check API key or rate limits",
#             reasoning=str(e),
#             signals_used=[],
#             recommended_action="Retry analysis",
#             confidence="low",
#             timestamp=datetime.utcnow().isoformat()
#         )


# # ── Full Pipeline ──────────────────────────────────────────────────────────────

# def run_company_analysis(company: dict, log_cb=None, force: bool = False) -> dict:
#     """
#     Full pipeline for one company: collect → analyse → persist.
#     Returns dict with snapshot + health.
#     """
#     def log(msg: str):
#         logger.info(msg)
#         if log_cb:
#             log_cb(msg)

#     name = company["name"]

#     if not force and has_recent_data(name, hours=6):
#         log(f"[CACHE] {name} has fresh data (< 6h old) — skipping collection")
#         return None  # caller should use DB data

#     log(f"\n{'='*50}")
#     log(f"Analysing: {name}")
#     log(f"{'='*50}")

#     snapshot = collect_signals(company, log_cb=log_cb)
#     health = analyze_with_claude(company, snapshot, log_cb=log_cb)
#     save_report(name, snapshot.model_dump(), health.model_dump())
#     log(f"[DONE] {name} saved to DB ✓\n")

#     return {"snapshot": snapshot.model_dump(), "health": health.model_dump()}


# def run_full_portfolio(companies: list[dict], log_cb=None, force: bool = False) -> list[dict]:
#     results = []
#     for company in companies:
#         result = run_company_analysis(company, log_cb=log_cb, force=force)
#         results.append(result)
#     return results



"""
Portfolio Health Monitor — Core Agent
Collects multi-source signals per company, then runs a single structured
Claude call to interpret them holistically. Not LangChain — raw API calls,
full control, full visibility.
"""
import os
import time
import json
import logging
from datetime import datetime
from typing import Generator
from duckduckgo_search import DDGS
from groq import Groq
from dotenv import load_dotenv
from app.models import SignalSnapshot, HealthSummary
from app.database import save_report, has_recent_data
from app.logging_utils import log_event
from app.alerts import notify_if_red

load_dotenv()
logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Configurable so a Groq model deprecation (has happened twice already) is a
# one-line .env change instead of a code hunt. openai/gpt-oss-120b is Groq's
# current flagship open-weight model with structured_outputs/json_mode
# support, which the JSON health-summary output here relies on.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


# ── Signal Collection ──────────────────────────────────────────────────────────

def _search(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo search with graceful rate-limit handling."""
    start = time.time()
    try:
        time.sleep(1.2)  # avoid DDG rate limits
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        log_event("ddg_search", query, len(results), (time.time() - start) * 1000)
        return results
    except Exception as e:
        logger.warning(f"Search failed for '{query}': {e}")
        log_event("ddg_search", query, 0, (time.time() - start) * 1000, error=str(e))
        return []


def collect_signals(company: dict, log_cb=None) -> SignalSnapshot:
    """
    Agentic signal collection loop. Each step informs the next.
    log_cb: optional callable(str) for streaming log lines to UI.
    """
    def log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    name = company["name"]
    history = company["headcount_history"]
    current_hc = history[-1]
    prev_hc = history[-2] if len(history) >= 2 else current_hc
    delta_pct = round(((current_hc - prev_hc) / prev_hc) * 100, 1) if prev_hc else 0

    log(f"[STEP 1] Collecting headcount signal for {name}...")
    log(f"[STEP 1] Headcount: {prev_hc} → {current_hc} ({delta_pct:+.1f}%)")

    log(f"[STEP 2] Searching recent news for {name}...")
    news_results = _search(f'"{name}" news 2025', max_results=5)
    headlines = [r.get("title", "") for r in news_results if r.get("title")]
    log(f"[STEP 2] Found {len(headlines)} news mentions: {headlines[:2]}")

    log(f"[STEP 3] Searching job postings for {name}...")
    job_results = _search(f'"{name}" hiring jobs 2025 site:linkedin.com OR site:greenhouse.io OR site:lever.co', max_results=6)
    # Also try a broader search if narrow one returns nothing
    if len(job_results) < 2:
        job_results = _search(f'"{name}" is hiring 2025', max_results=5)
    job_titles = [r.get("title", "") for r in job_results if r.get("title")]
    log(f"[STEP 3] Found {len(job_titles)} job posting signals")

    # Step 4: GitHub activity if available
    github_commits = None
    if company.get("github"):
        log(f"[STEP 4] Searching GitHub activity for {company['github']}...")
        gh_results = _search(f'site:github.com/{company["github"]} commits 2025', max_results=3)
        github_commits = len(gh_results) * 3  # rough proxy
        log(f"[STEP 4] GitHub activity proxy score: {github_commits}")
    else:
        log(f"[STEP 4] No GitHub handle — skipping open-source activity check")

    snapshot = SignalSnapshot(
        company_name=name,
        timestamp=datetime.utcnow().isoformat(),
        headcount_current=current_hc,
        headcount_previous=prev_hc,
        headcount_delta_pct=delta_pct,
        news_count=len(headlines),
        news_headlines=headlines[:5],
        job_postings_count=len(job_titles),
        job_titles_sample=job_titles[:5],
        github_commits_week=github_commits,
    )
    log(f"[STEP 4] Signal collection complete ✓")
    return snapshot


# ── Claude Analysis ────────────────────────────────────────────────────────────

def analyze_with_claude(company: dict, snapshot: SignalSnapshot, log_cb=None) -> HealthSummary:
    """
    Single Claude call with all signals. Returns structured HealthSummary.
    Reasoning is extracted directly from the response — no hidden chain-of-thought.
    """
    def log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    log(f"[CLAUDE] Synthesising signals for {company['name']}...")

    prompt = f"""You are a portfolio health analyst for Together Fund, an AI-first VC in India.
Analyse the following signals for portfolio company "{company['name']}" ({company['sector']}, founded {company['founded']}, last funding: {company['last_funding']}).

SIGNALS THIS WEEK:
- Headcount: {snapshot.headcount_previous} → {snapshot.headcount_current} ({snapshot.headcount_delta_pct:+.1f}%)
- News mentions (last 30 days): {snapshot.news_count}
- News headlines: {json.dumps(snapshot.news_headlines)}
- Job postings found: {snapshot.job_postings_count}
- Job titles sample: {json.dumps(snapshot.job_titles_sample)}
- GitHub activity proxy: {snapshot.github_commits_week if snapshot.github_commits_week is not None else "N/A (not open source)"}
- Headcount trend (last 6 months): {company['headcount_history']}

TASK: Provide a structured health assessment. Think step by step before concluding.
Consider: Is headcount growth healthy or declining? Is hiring aggressive (growth signal) or absent (stagnation)? Are there news signals of traction or distress? How does this compare to stage and sector norms?

Respond ONLY with valid JSON matching this schema exactly:
{{
  "status": "green" | "yellow" | "red",
  "headline": "one crisp sentence verdict under 20 words",
  "reasoning": "2-4 sentence analytical reasoning citing specific signals",
  "signals_used": ["list of 2-4 key signals that drove your verdict"],
  "recommended_action": "one concrete action for the partner",
  "confidence": "high" | "medium" | "low"
}}"""

    start = time.time()
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        log(f"[CLAUDE] Status: {data['status'].upper()} — {data['headline']}")
        log_event("groq_llm", prompt, len(raw), (time.time() - start) * 1000,
                   model=GROQ_MODEL, company=company["name"])
        return HealthSummary(
            company_name=company["name"],
            timestamp=datetime.utcnow().isoformat(),
            **data
        )
    except Exception as e:
        logger.error(f"Claude analysis failed for {company['name']}: {e}")
        log_event("groq_llm", prompt, 0, (time.time() - start) * 1000,
                   model=GROQ_MODEL, company=company["name"], error=str(e))
        return HealthSummary(
            company_name=company["name"],
            status="yellow",
            headline="Analysis unavailable — check API key or rate limits",
            reasoning=str(e),
            signals_used=[],
            recommended_action="Retry analysis",
            confidence="low",
            timestamp=datetime.utcnow().isoformat()
        )


# ── Full Pipeline ──────────────────────────────────────────────────────────────

def run_company_analysis(company: dict, log_cb=None, force: bool = False) -> dict:
    """
    Full pipeline for one company: collect → analyse → persist.
    Returns dict with snapshot + health.
    """
    def log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    name = company["name"]

    if not force and has_recent_data(name, hours=6):
        log(f"[CACHE] {name} has fresh data (< 6h old) — skipping collection")
        return None  # caller should use DB data

    log(f"\n{'='*50}")
    log(f"Analysing: {name}")
    log(f"{'='*50}")

    snapshot = collect_signals(company, log_cb=log_cb)
    health = analyze_with_claude(company, snapshot, log_cb=log_cb)
    save_report(name, snapshot.model_dump(), health.model_dump())
    notify_if_red(name, health.status, health.headline)
    log(f"[DONE] {name} saved to DB ✓\n")

    return {"snapshot": snapshot.model_dump(), "health": health.model_dump()}


def run_full_portfolio(companies: list[dict], log_cb=None, force: bool = False) -> list[dict]:
    results = []
    for company in companies:
        result = run_company_analysis(company, log_cb=log_cb, force=force)
        results.append(result)
    return results