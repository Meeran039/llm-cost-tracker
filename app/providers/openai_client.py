"""
Client for OpenAI's Admin Costs API.

Real, documented endpoint (verified against OpenAI's API reference,
not guessed): https://developers.openai.com/api/reference/resources/
admin/subresources/organization/subresources/usage/methods/costs

IMPORTANT: this requires an Admin API key (created in Organization
Settings), NOT a regular API key. A regular key will be rejected with
a 401, which we translate into a clear, specific error below.
"""

import httpx
from datetime import datetime, timezone

OPENAI_COSTS_URL = "https://api.openai.com/v1/organization/costs"


class OpenAIAdminKeyError(Exception):
    """Raised when the provided key is rejected -- almost always means
    a regular API key was used where an Admin API key is required."""


class OpenAIAPIError(Exception):
    """Raised for any other non-success response from OpenAI's API."""


def get_openai_costs(
    admin_api_key: str,
    start_time: datetime,
    end_time: datetime | None = None,
    client: httpx.Client | None = None,
) -> list[dict]:
    """
    Returns a list of {"date": "YYYY-MM-DD", "cost_usd": float}, one
    entry per day bucket, summing all line items within that bucket.

    `client` can be injected for testing (see tests/test_openai_client.py),
    production code should leave it as None to use a real httpx.Client.
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=15.0)

    daily_totals: dict[str, float] = {}
    params: dict = {
        "start_time": int(start_time.replace(tzinfo=timezone.utc).timestamp()),
        "bucket_width": "1d",
        "limit": 180,
    }
    if end_time:
        params["end_time"] = int(end_time.replace(tzinfo=timezone.utc).timestamp())

    headers = {"Authorization": f"Bearer {admin_api_key}"}

    try:
        next_page = None
        while True:
            request_params = dict(params)
            if next_page:
                request_params["page"] = next_page

            response = client.get(OPENAI_COSTS_URL, params=request_params, headers=headers)

            if response.status_code == 401:
                raise OpenAIAdminKeyError(
                    "OpenAI rejected this key. Make sure you're using an Admin API key "
                    "(created under Organization Settings -> Admin keys), not a regular "
                    "project API key -- regular keys cannot access cost data."
                )
            if response.status_code != 200:
                raise OpenAIAPIError(
                    f"OpenAI Costs API returned {response.status_code}: {response.text}"
                )

            payload = response.json()

            for bucket in payload.get("data", []):
                bucket_date = datetime.fromtimestamp(
                    bucket["start_time"], tz=timezone.utc
                ).strftime("%Y-%m-%d")
                bucket_total = sum(
                    (result.get("amount") or {}).get("value", 0.0)
                    for result in bucket.get("results", [])
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