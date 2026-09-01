"""
MCP server for the LLM Cost Tracker.

Wraps the same underlying data (usage_records, populated by POST
/usage/log) as MCP tools, so any MCP-compatible client (e.g. Claude
Desktop) can ask about spend conversationally, independent of the web
dashboard.

Authentication here uses a per-user API key (generated via POST
/api-keys on the REST API), NOT the JWT session tokens used by the web
dashboard -- MCP clients can't do an interactive login redirect, so a
long-lived key is the right fit here.

Run with:
    python app/mcp_server.py
"""

from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP

from app.database import SessionLocal
from app.models import UsageRecord
from app.security import authenticate_mcp_api_key
from app.agents.pattern_finder import find_patterns
from app.agents.recommender import generate_recommendation

mcp = FastMCP("LLM Cost Tracker")


@mcp.tool()
def get_usage_summary(api_key: str, days: int = 30) -> str:
    """
    Get a summary of LLM API spend across connected providers
    (OpenAI, Anthropic) for the authenticated user, over the last
    `days` days. Reads from logged data -- log usage first via
    POST /usage/log if nothing shows up.
    """
    db = SessionLocal()
    try:
        user = authenticate_mcp_api_key(db, api_key)
        if not user:
            return "Invalid API key. Generate one from the dashboard under Settings -> API Keys."

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        records = (
            db.query(UsageRecord)
            .filter(UsageRecord.user_id == user.id, UsageRecord.date >= cutoff)
            .all()
        )

        if not records:
            return (
                f"No usage data found for the last {days} days. "
                "Log usage via POST /usage/log first."
            )

        by_provider: dict[str, float] = {}
        for r in records:
            by_provider[r.provider] = round(by_provider.get(r.provider, 0.0) + r.cost_usd, 6)
        total = round(sum(by_provider.values()), 6)

        lines = [f"Total spend over the last {days} days: ${total}"]
        for provider, cost in sorted(by_provider.items()):
            lines.append(f"  {provider}: ${cost}")

        return "\n".join(lines)
    finally:
        db.close()


@mcp.tool()
def get_cost_advice(api_key: str) -> str:
    """
    Analyzes the authenticated user's logged usage and returns a
    data-grounded, plain-English cost optimization suggestion, the same
    logic behind the /advisor REST endpoint. Recommendations are based
    only on the user's own real usage data, never external claims about
    model quality.
    """
    db = SessionLocal()
    try:
        user = authenticate_mcp_api_key(db, api_key)
        if not user:
            return "Invalid API key. Generate one from the dashboard under Settings -> API Keys."

        records = db.query(UsageRecord).filter(UsageRecord.user_id == user.id).all()
        usage_dicts = [{"provider": r.provider, "cost_usd": r.cost_usd, "tokens": r.tokens or 0} for r in records]

        pattern = find_patterns(usage_dicts)
        return generate_recommendation(pattern)
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()