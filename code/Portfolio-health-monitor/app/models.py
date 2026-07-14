from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SignalSnapshot(BaseModel):
    company_name: str
    timestamp: str
    headcount_current: int
    headcount_previous: int
    headcount_delta_pct: float
    news_count: int
    news_headlines: list[str]
    job_postings_count: int
    job_titles_sample: list[str]
    github_commits_week: Optional[int] = None


class HealthSummary(BaseModel):
    company_name: str
    status: str               # "green" | "yellow" | "red"
    headline: str             # one-line verdict
    reasoning: str            # Claude's full chain-of-thought
    signals_used: list[str]   # which signals drove the verdict
    recommended_action: str
    confidence: str           # "high" | "medium" | "low"
    timestamp: str


class CompanyReport(BaseModel):
    company: dict
    snapshot: SignalSnapshot
    health: HealthSummary