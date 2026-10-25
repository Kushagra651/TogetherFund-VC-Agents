"""
Structured JSONL logging for every external tool call (DDG search, Groq call).
Same pattern as dd-agent/agent/logging_utils.py — one function, no external
dependency, appended to logs/portfolio_monitor.jsonl at the repo root.
"""
import json
import time
import os

LOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "logs", "portfolio_monitor.jsonl"
)


def log_event(tool: str, input_data, output_len: int, latency_ms: float, **extra):
    """Append one structured JSON line. Never raises — logging must not break the agent."""
    event = {
        "timestamp": time.time(),
        "tool": tool,
        "input": input_data if isinstance(input_data, str) else json.dumps(input_data)[:500],
        "output_len": output_len,
        "latency_ms": round(latency_ms, 1),
    }
    event.update(extra)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass
