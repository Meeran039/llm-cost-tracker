"""
Tests the Anthropic cost client against mocked responses shaped exactly
like Anthropic's real documented API (see anthropic_client.py's docstring
for the verified reference URL). Never hits the real network or real
billing data.
"""

import httpx
import pytest
from datetime import datetime, timezone

from app.providers.anthropic_client import (
    get_anthropic_costs, AnthropicAdminKeyError, AnthropicAPIError,
)


def make_mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestAnthropicCosts:
    def test_string_amount_is_correctly_converted_to_float(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "data": [{
                        "starting_at": "2025-08-01T00:00:00Z",
                        "ending_at": "2025-08-02T00:00:00Z",
                        "results": [
                            {"amount": "123.78912", "currency": "USD", "cost_type": "tokens",
                             "description": "Claude Opus 5 Usage - Input Tokens"},
                        ],
                    }],
                    "has_more": False,
                    "next_page": None,
                },
            )

        client = make_mock_client(handler)
        result = get_anthropic_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2025, 8, 1, tzinfo=timezone.utc),
            client=client,
        )

        assert result == [{"date": "2025-08-01", "cost_usd": 123.78912}]
        assert isinstance(result[0]["cost_usd"], float)

    def test_sums_multiple_line_items_in_one_bucket(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "data": [{
                        "starting_at": "2025-08-01T00:00:00Z",
                        "ending_at": "2025-08-02T00:00:00Z",
                        "results": [
                            {"amount": "10.00", "description": "Input Tokens"},
                            {"amount": "5.50", "description": "Output Tokens"},
                        ],
                    }],
                    "has_more": False,
                    "next_page": None,
                },
            )

        client = make_mock_client(handler)
        result = get_anthropic_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2025, 8, 1, tzinfo=timezone.utc),
            client=client,
        )
        assert result == [{"date": "2025-08-01", "cost_usd": 15.5}]

    def test_follows_pagination_across_low_default_limit(self):
        call_count = {"n": 0}

        def handler(request):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return httpx.Response(
                    200,
                    json={
                        "data": [{
                            "starting_at": "2025-08-01T00:00:00Z", "ending_at": "2025-08-02T00:00:00Z",
                            "results": [{"amount": "1.00", "description": "Input Tokens"}],
                        }],
                        "has_more": True,
                        "next_page": "page_abc123",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "data": [{
                        "starting_at": "2025-08-02T00:00:00Z", "ending_at": "2025-08-03T00:00:00Z",
                        "results": [{"amount": "2.00", "description": "Input Tokens"}],
                    }],
                    "has_more": False,
                    "next_page": None,
                },
            )

        client = make_mock_client(handler)
        result = get_anthropic_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2025, 8, 1, tzinfo=timezone.utc),
            client=client,
        )

        assert call_count["n"] == 2
        assert len(result) == 2

    def test_regular_api_key_raises_clear_admin_key_error(self):
        def handler(request):
            return httpx.Response(401, json={"error": {"message": "authentication_error"}})

        client = make_mock_client(handler)
        with pytest.raises(AnthropicAdminKeyError, match="Admin API key"):
            get_anthropic_costs(
                admin_api_key="sk-ant-regular-key-not-admin",
                start_time=datetime(2025, 8, 1, tzinfo=timezone.utc),
                client=client,
            )

    def test_sends_required_headers(self):
        captured_headers = {}

        def handler(request):
            captured_headers.update(request.headers)
            return httpx.Response(200, json={"data": [], "has_more": False, "next_page": None})

        client = make_mock_client(handler)
        get_anthropic_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2025, 8, 1, tzinfo=timezone.utc),
            client=client,
        )

        assert captured_headers.get("x-api-key") == "sk-ant-admin-fake"
        assert captured_headers.get("anthropic-version") == "2023-06-01"

    def test_other_error_status_raises_generic_api_error(self):
        def handler(request):
            return httpx.Response(500, text="Internal Server Error")

        client = make_mock_client(handler)
        with pytest.raises(AnthropicAPIError):
            get_anthropic_costs(
                admin_api_key="sk-ant-admin-fake",
                start_time=datetime(2025, 8, 1, tzinfo=timezone.utc),
                client=client,
            )

    def test_empty_data_returns_empty_list(self):
        def handler(request):
            return httpx.Response(200, json={"data": [], "has_more": False, "next_page": None})

        client = make_mock_client(handler)
        result = get_anthropic_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2025, 8, 1, tzinfo=timezone.utc),
            client=client,
        )
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])