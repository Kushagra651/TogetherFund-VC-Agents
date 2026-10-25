"""
Eval harness for the DD Research Agent.

Runs the agent on a fixed golden set of 5 real companies with known
ground-truth fields, scores field-level accuracy (founder / funding /
product), and writes a timestamped results record.

Usage:
    cd dd-agent  (or code/Due-Dilligence-Agent)
    python -m eval.run_eval

This hits real Groq + Tavily APIs (no mocking) because the point is to
measure the live agent's factual reliability, not a frozen fixture. Each
company run takes ~20-40s (5 search steps + synthesis). The CI workflow
(.github/workflows/eval.yml) runs this same script on every push to main.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.core import run_agent  # noqa: E402

GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "golden_set.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")


def _score_company(case: dict) -> dict:
    """Runs the agent on one golden-set company and scores each field."""
    memo = None
    for event in run_agent(case["company"], case["description"], case["founder_linkedin"]):
        if event["type"] == "memo":
            memo = event["memo"]
        elif event["type"] == "error":
            print(f"  [warn] {case['company']} step error: {event['message']}")

    if memo is None:
        return {
            "company": case["company"],
            "memo_generated": False,
            "founder_correct": False,
            "funding_correct": False,
            "product_correct": False,
            "field_scores": {"founder": 0, "funding": 0, "product": 0},
        }

    founder_text = memo.founder.lower()
    traction_market_text = (memo.traction + " " + memo.market).lower()
    product_text = memo.market.lower()

    founder_correct = case["expected_founder_keyword"].lower() in founder_text
    funding_correct = case["expected_funding_keyword"].lower() in traction_market_text
    product_correct = any(
        kw.lower() in product_text for kw in case["expected_product_keywords"]
    )

    return {
        "company": case["company"],
        "memo_generated": True,
        "founder_correct": founder_correct,
        "funding_correct": funding_correct,
        "product_correct": product_correct,
        "confidence": memo.confidence,
        "field_scores": {
            "founder": int(founder_correct),
            "funding": int(funding_correct),
            "product": int(product_correct),
        },
    }


def run_eval() -> dict:
    with open(GOLDEN_SET_PATH) as f:
        golden_set = json.load(f)

    per_company = []
    for case in golden_set:
        print(f"[eval] running {case['company']}...")
        per_company.append(_score_company(case))

    n = len(per_company)
    generated = sum(1 for r in per_company if r["memo_generated"])
    field_accuracy = {
        "founder": sum(r["field_scores"]["founder"] for r in per_company) / n,
        "funding": sum(r["field_scores"]["funding"] for r in per_company) / n,
        "product": sum(r["field_scores"]["product"] for r in per_company) / n,
    }
    # Overall memo accuracy = mean of the three per-field accuracies.
    overall_accuracy = sum(field_accuracy.values()) / len(field_accuracy)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_companies": n,
        "memos_generated": generated,
        "field_accuracy": field_accuracy,
        "overall_memo_accuracy": round(overall_accuracy, 3),
        "per_company": per_company,
    }
    return result


def _append_results(result: dict):
    history = []
    if os.path.exists(RESULTS_PATH):
        try:
            with open(RESULTS_PATH) as f:
                history = json.load(f)
            if not isinstance(history, list):
                history = [history]
        except (json.JSONDecodeError, ValueError):
            history = []
    history.append(result)
    with open(RESULTS_PATH, "w") as f:
        json.dump(history, f, indent=2)


if __name__ == "__main__":
    result = run_eval()
    _append_results(result)

    print("\n" + "=" * 50)
    print(f"Overall memo accuracy: {result['overall_memo_accuracy']:.0%}")
    print(f"  founder: {result['field_accuracy']['founder']:.0%}")
    print(f"  funding: {result['field_accuracy']['funding']:.0%}")
    print(f"  product: {result['field_accuracy']['product']:.0%}")
    print("=" * 50)

    # CI gate: fail if overall accuracy drops below 0.75
    if result["overall_memo_accuracy"] < 0.75:
        print("FAIL: overall memo accuracy below 0.75 threshold")
        sys.exit(1)
    print("PASS")
