import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "portfolio.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                health_json TEXT NOT NULL
            )
        """)
        conn.commit()


def save_report(company_name: str, snapshot: dict, health: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO snapshots (company_name, timestamp, snapshot_json, health_json) VALUES (?,?,?,?)",
            (company_name, datetime.utcnow().isoformat(), json.dumps(snapshot), json.dumps(health))
        )
        conn.commit()


def get_latest_reports() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT s.* FROM snapshots s
            INNER JOIN (
                SELECT company_name, MAX(timestamp) as mt FROM snapshots GROUP BY company_name
            ) latest ON s.company_name = latest.company_name AND s.timestamp = latest.mt
            ORDER BY s.company_name
        """).fetchall()
    return [{"company_name": r["company_name"], "timestamp": r["timestamp"],
             "snapshot": json.loads(r["snapshot_json"]), "health": json.loads(r["health_json"])}
            for r in rows]


def get_company_history(company_name: str, limit: int = 8) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE company_name=? ORDER BY timestamp DESC LIMIT ?",
            (company_name, limit)
        ).fetchall()
    return [{"timestamp": r["timestamp"], "snapshot": json.loads(r["snapshot_json"]),
             "health": json.loads(r["health_json"])} for r in rows]


def has_recent_data(company_name: str, hours: int = 6) -> bool:
    """Returns True if data was collected within `hours` ago."""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT timestamp FROM snapshots WHERE company_name=? ORDER BY timestamp DESC LIMIT 1",
            (company_name,)
        ).fetchone()
    if not row:
        return False
    from datetime import timezone, timedelta
    last = datetime.fromisoformat(row[0])
    return (datetime.utcnow() - last) < timedelta(hours=hours)