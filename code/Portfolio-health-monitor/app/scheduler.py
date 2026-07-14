import json
import logging
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from app.monitor import run_full_portfolio

logger = logging.getLogger(__name__)
COMPANIES_PATH = Path(__file__).parent.parent / "data" / "companies.json"


def _load_companies() -> list[dict]:
    return json.loads(COMPANIES_PATH.read_text())


def weekly_refresh():
    logger.info("Scheduler: starting weekly portfolio refresh...")
    companies = _load_companies()
    run_full_portfolio(companies, force=True)
    logger.info("Scheduler: weekly refresh complete.")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # Run every Monday at 07:00 AM
    scheduler.add_job(weekly_refresh, "cron", day_of_week="mon", hour=7, minute=0)
    scheduler.start()
    logger.info("Scheduler started — next run: Monday 07:00 AM")
    return scheduler