"""
MCP server for the LLM Cost Tracker.

Wraps the same underlying data (usage_records, populated by the /usage/*
REST endpoints) as MCP tools, so any MCP-compatible client (e.g. Claude
Desktop) can ask about spend conversationally, independent of the web
dashboard.

Authentication here uses a per-user API key (generated via POST
/api-keys on the REST API), NOT the JWT session tokens used by the web
dashboard -- MCP clients can't do an interactive login redirect, so a
long-lived key is the right fit here, same pattern used in the chess
coach project's MCP server.

Run with:
    python app/mcp_server.py
"""

from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP

from app.database import SessionLocal
from app.models import UsageRecord
from app.security import authenticate_mcp_api_key

mcp = FastMCP("LLM Cost Tracker")


@mcp.tool()
def get_usage_summary(api_key: str, days: int = 30) -> str:
    """
    Get a summary of LLM API spend across connected providers
    (OpenAI, Anthropic) for the authenticated user, over the last
    `days` days. Reads from cached data -- if a provider hasn't been
    refreshed recently via the dashboard, figures may be stale.
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
                "Try refreshing via the dashboard or GET /usage/openai and /usage/anthropic first."
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


if __name__ == "__main__":
    mcp.run()