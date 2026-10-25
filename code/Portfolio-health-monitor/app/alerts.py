"""
Slack webhook alerts for portfolio health status changes.

Fires only on red-status flips — not on every run — so the channel stays
signal, not noise. If SLACK_WEBHOOK_URL is unset, every call is a silent
no-op: the monitor must work identically with or without Slack configured.
"""
import os
import json
import logging
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def _previous_status(company_name: str) -> str | None:
    """Looks at the prior saved snapshot to detect a flip (not just 'is red')."""
    from app.database import get_company_history
    history = get_company_history(company_name, limit=2)
    # history[0] is the row just saved by run_company_analysis; history[1] is the one before it
    if len(history) < 2:
        return None
    return history[1]["health"].get("status")


def _post_to_slack(payload: dict) -> bool:
    try:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning(f"Slack webhook post failed: {e}")
        return False


def notify_if_red(company_name: str, status: str, reason: str):
    """
    Posts a Slack message when a company flips TO red status this run.
    Skips silently if SLACK_WEBHOOK_URL is not set — never crashes the pipeline.
    """
    if not SLACK_WEBHOOK_URL:
        return

    if status != "red":
        return

    prev = _previous_status(company_name)
    if prev == "red":
        # Already red last run — don't re-alert every single run.
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    text = (
        f":red_circle: *{company_name}* flipped to *RED*\n"
        f"> {reason}\n"
        f"_{timestamp}_"
    )
    ok = _post_to_slack({"text": text})
    if ok:
        logger.info(f"[ALERT] Slack notified: {company_name} → red")
    else:
        logger.warning(f"[ALERT] Slack notification failed for {company_name}")
