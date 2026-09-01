"""
Deterministic analysis of a user's logged usage history. Deliberately
NOT an LLM call -- pure math/aggregation.
"""

from collections import defaultdict


def find_patterns(usage_records: list[dict]) -> dict:
    if not usage_records:
        return {
            "total_calls": 0,
            "total_cost_usd": 0.0,
            "by_provider": {},
            "highest_spend_provider": None,
            "avg_cost_per_call": 0.0,
        }

    by_provider = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0, "tokens": 0})
    for r in usage_records:
        p = by_provider[r["provider"]]
        p["calls"] += 1
        p["cost_usd"] += r["cost_usd"]
        p["tokens"] += r.get("tokens", 0)

    for p in by_provider.values():
        p["cost_usd"] = round(p["cost_usd"], 6)
        p["avg_cost_per_call"] = round(p["cost_usd"] / p["calls"], 6) if p["calls"] else 0.0

    total_cost = round(sum(p["cost_usd"] for p in by_provider.values()), 6)
    total_calls = sum(p["calls"] for p in by_provider.values())
    highest = max(by_provider.items(), key=lambda kv: kv[1]["cost_usd"])[0] if by_provider else None

    return {
        "total_calls": total_calls,
        "total_cost_usd": total_cost,
        "by_provider": dict(by_provider),
        "highest_spend_provider": highest,
        "avg_cost_per_call": round(total_cost / total_calls, 6) if total_calls else 0.0,
    }