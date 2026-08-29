"""
Tests the OpenAI cost client against mocked responses shaped exactly like
OpenAI's real documented API (see openai_client.py's docstring for the
verified reference URL). Never hits the real network or real billing data.
"""

import httpx
import pytest
from datetime import datetime, timezone

from app.providers.openai_client import get_openai_costs, OpenAIAdminKeyError, OpenAIAPIError


def make_mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestOpenAICosts:
    def test_parses_single_bucket_correctly(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "object": "page",
                    "data": [
                        {
                            "object": "bucket",
                            "start_time": 1730419200,  # 2024-11-01 00:00:00 UTC
                            "end_time": 1730505600,
                            "results": [
                                {"object": "organization.costs.result", "amount": {"currency": "usd", "value": 1.25}},
                                {"object": "organization.costs.result", "amount": {"currency": "usd", "value": 0.75}},
                            ],
                        }
                    ],
                    "has_more": False,
                    "next_page": None,
                },
            )

        client = make_mock_client(handler)
        result = get_openai_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
            client=client,
        )

        assert result == [{"date": "2024-11-01", "cost_usd": 2.0}]

    def test_sums_multiple_buckets(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "object": "page",
                    "data": [
                        {
                            "object": "bucket", "start_time": 1730419200, "end_time": 1730505600,
                            "results": [{"object": "organization.costs.result", "amount": {"currency": "usd", "value": 5.0}}],
                        },
                        {
                            "object": "bucket", "start_time": 1730505600, "end_time": 1730592000,
                            "results": [{"object": "organization.costs.result", "amount": {"currency": "usd", "value": 3.5}}],
                        },
                    ],
                    "has_more": False,
                    "next_page": None,
                },
            )

        client = make_mock_client(handler)
        result = get_openai_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
            client=client,
        )

        assert len(result) == 2
        assert result[0]["cost_usd"] == 5.0
        assert result[1]["cost_usd"] == 3.5

    def test_follows_pagination(self):
        call_count = {"n": 0}

        def handler(request):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return httpx.Response(
                    200,
                    json={
                        "object": "page",
                        "data": [{
                            "object": "bucket", "start_time": 1730419200, "end_time": 1730505600,
                            "results": [{"object": "organization.costs.result", "amount": {"currency": "usd", "value": 1.0}}],
                        }],
                        "has_more": True,
                        "next_page": "page_2_token",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "object": "page",
                    "data": [{
                        "object": "bucket", "start_time": 1730505600, "end_time": 1730592000,
                        "results": [{"object": "organization.costs.result", "amount": {"currency": "usd", "value": 2.0}}],
                    }],
                    "has_more": False,
                    "next_page": None,
                },
            )

        client = make_mock_client(handler)
        result = get_openai_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
            client=client,
        )

        assert call_count["n"] == 2, "Should have followed pagination to a second page"
        assert len(result) == 2

    def test_regular_api_key_raises_clear_admin_key_error(self):
        def handler(request):
            return httpx.Response(401, json={"error": {"message": "Invalid authentication"}})

        client = make_mock_client(handler)
        with pytest.raises(OpenAIAdminKeyError, match="Admin API key"):
            get_openai_costs(
                admin_api_key="sk-regular-key-not-admin",
                start_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
                client=client,
            )

    def test_other_error_status_raises_generic_api_error(self):
        def handler(request):
            return httpx.Response(500, text="Internal Server Error")

        client = make_mock_client(handler)
        with pytest.raises(OpenAIAPIError):
            get_openai_costs(
                admin_api_key="sk-ant-admin-fake",
                start_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
                client=client,
            )

    def test_empty_data_returns_empty_list(self):
        def handler(request):
            return httpx.Response(200, json={"object": "page", "data": [], "has_more": False, "next_page": None})

        client = make_mock_client(handler)
        result = get_openai_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
            client=client,
        )
        assert result == []

    def test_missing_amount_defaults_to_zero_not_a_crash(self):
        """A result with no 'amount' field at all should be treated as $0, not crash."""
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "object": "page",
                    "data": [{
                        "object": "bucket", "start_time": 1730419200, "end_time": 1730505600,
                        "results": [{"object": "organization.costs.result"}],
                    }],
                    "has_more": False,
                    "next_page": None,
                },
            )

        client = make_mock_client(handler)
        result = get_openai_costs(
            admin_api_key="sk-ant-admin-fake",
            start_time=datetime(2024, 11, 1, tzinfo=timezone.utc),
            client=client,
        )
        assert result == [{"date": "2024-11-01", "cost_usd": 0.0}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])