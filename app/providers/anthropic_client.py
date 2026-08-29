"""
Client for Anthropic's Admin Cost Report API.

Real, documented endpoint (verified against Anthropic's API reference,
not guessed): https://platform.claude.com/docs/en/api/admin/cost_report/retrieve

IMPORTANT differences from OpenAI's equivalent endpoint, verified from
the docs, not assumed:
  - Auth uses the `x-api-key` header (plus a required `anthropic-version`
    header), not `Authorization: Bearer`.
  - `amount` is returned as a STRING (e.g. "123.78912"), not a float --
    must be explicitly converted, or cost totals will silently be wrong
    (string concatenation / comparison bugs) or crash.
  - Time buckets use `starting_at` / `ending_at` as ISO 8601 timestamps,
    not Unix seconds like OpenAI.
  - Default page size is only 7 buckets (max 31), so pagination kicks in
    much sooner than OpenAI's default of 180 -- a 30-day query WILL
    paginate under normal use, this isn't just an edge case here.
  - Requires an Admin API key (starts `sk-ant-admin`), not a regular key.
"""

import httpx
from datetime import datetime, timezone

ANTHROPIC_COST_REPORT_URL = "https://api.anthropic.com/v1/organizations/cost_report"
ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicAdminKeyError(Exception):
    """Raised when the provided key is rejected -- almost always means
    a regular API key was used where an Admin API key is required."""


class AnthropicAPIError(Exception):
    """Raised for any other non-success response from Anthropic's API."""


def get_anthropic_costs(
    admin_api_key: str,
    start_time: datetime,
    end_time: datetime | None = None,
    client: httpx.Client | None = None,
) -> list[dict]:
    """
    Returns a list of {"date": "YYYY-MM-DD", "cost_usd": float}, one
    entry per day bucket, summing all line items within that bucket.
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=15.0)

    daily_totals: dict[str, float] = {}
    params: dict = {
        "starting_at": start_time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bucket_width": "1d",
        "limit": 31,
    }
    if end_time:
        params["ending_at"] = end_time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    headers = {
        "x-api-key": admin_api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
    }

    try:
        next_page = None
        while True:
            request_params = dict(params)
            if next_page:
                request_params["page"] = next_page

            response = client.get(ANTHROPIC_COST_REPORT_URL, params=request_params, headers=headers)

            if response.status_code == 401:
                raise AnthropicAdminKeyError(
                    "Anthropic rejected this key. Make sure you're using an Admin API key "
                    "(starts with sk-ant-admin, created under Console -> Settings -> Admin keys), "
                    "not a regular or workspace API key -- those cannot access cost data."
                )
            if response.status_code != 200:
                raise AnthropicAPIError(
                    f"Anthropic Cost Report API returned {response.status_code}: {response.text}"
                )

            payload = response.json()

            for bucket in payload.get("data", []):
                bucket_date = bucket["starting_at"][:10]
                bucket_total = sum(
                    float(result["amount"])
                    for result in bucket.get("results", [])
                    if result.get("amount") is not None
                )
                daily_totals[bucket_date] = daily_totals.get(bucket_date, 0.0) + bucket_total

            if payload.get("has_more") and payload.get("next_page"):
                next_page = payload["next_page"]
            else:
                break
    finally:
        if owns_client:
            client.close()

    return [
        {"date": date, "cost_usd": round(total, 6)}
        for date, total in sorted(daily_totals.items())
    ]