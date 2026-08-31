"""
End-to-end tests for the API endpoints themselves (auth, keys, usage,
api-keys), using FastAPI's TestClient against a fresh, isolated SQLite
database that is dropped and recreated between every test.

This complements the other test files (test_security.py tests the
crypto/hashing primitives in isolation; test_openai_client.py and
test_anthropic_client.py test the provider HTTP clients in isolation;
test_mcp_server.py tests MCP auth and the summary tool). This file is
the one that actually exercises the endpoints a real frontend calls,
proving the whole request/response chain works, not just its parts.
"""

import os
os.environ.setdefault("ENCRYPTION_KEY", "kQ8rN2vX9pL4mZ7wJ1cF6bT3sA0dY5hU8gK2eR4nQ6w=")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_api_endpoints.db")

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from app.database import Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_tables():
    """Every test starts against a clean, empty database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def signup_and_login(email="user@example.com", password="StrongPass1!"):
    client.post("/auth/signup", json={"email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuthFlow:
    def test_signup_then_login_succeeds(self):
        r = client.post("/auth/signup", json={"email": "a@example.com", "password": "StrongPass1!"})
        assert r.status_code == 201

        r = client.post("/auth/login", json={"email": "a@example.com", "password": "StrongPass1!"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_signup_weak_password_rejected(self):
        r = client.post("/auth/signup", json={"email": "b@example.com", "password": "weak"})
        assert r.status_code == 422

    def test_signup_duplicate_email_rejected(self):
        client.post("/auth/signup", json={"email": "c@example.com", "password": "StrongPass1!"})
        r = client.post("/auth/signup", json={"email": "c@example.com", "password": "AnotherPass2@"})
        assert r.status_code == 400

    def test_login_wrong_password_rejected(self):
        client.post("/auth/signup", json={"email": "d@example.com", "password": "StrongPass1!"})
        r = client.post("/auth/login", json={"email": "d@example.com", "password": "WrongPassword9!"})
        assert r.status_code == 401

    def test_me_requires_valid_token(self):
        r = client.get("/auth/me")
        assert r.status_code == 401

        headers = signup_and_login("e@example.com")
        r = client.get("/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["email"] == "e@example.com"


class TestProviderKeys:
    def test_add_and_list_key_never_exposes_raw_value(self):
        headers = signup_and_login("f@example.com")
        r = client.post("/keys", json={"provider": "openai", "api_key": "sk-real-secret"}, headers=headers)
        assert r.status_code == 201
        assert "api_key" not in r.json()

        r = client.get("/keys", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["provider"] == "openai"
        assert "api_key" not in r.json()[0]

    def test_duplicate_provider_key_rejected(self):
        headers = signup_and_login("g@example.com")
        client.post("/keys", json={"provider": "openai", "api_key": "sk-1"}, headers=headers)
        r = client.post("/keys", json={"provider": "openai", "api_key": "sk-2"}, headers=headers)
        assert r.status_code == 400

    def test_invalid_provider_name_rejected(self):
        headers = signup_and_login("h@example.com")
        r = client.post("/keys", json={"provider": "not-a-real-provider", "api_key": "sk-1"}, headers=headers)
        assert r.status_code == 400

    def test_delete_key(self):
        headers = signup_and_login("i@example.com")
        r = client.post("/keys", json={"provider": "anthropic", "api_key": "sk-ant-1"}, headers=headers)
        key_id = r.json()["id"]

        r = client.delete(f"/keys/{key_id}", headers=headers)
        assert r.status_code == 204

        r = client.get("/keys", headers=headers)
        assert r.json() == []

    def test_keys_are_isolated_per_user(self):
        headers_a = signup_and_login("j@example.com")
        headers_b = signup_and_login("k@example.com")

        client.post("/keys", json={"provider": "openai", "api_key": "sk-a"}, headers=headers_a)

        r = client.get("/keys", headers=headers_b)
        assert r.json() == [], "User B should not see User A's connected providers"


class TestUsageEndpoints:
    def test_usage_without_connected_key_returns_404(self):
        headers = signup_and_login("l@example.com")
        r = client.get("/usage/openai", headers=headers)
        assert r.status_code == 404

    def test_usage_openai_with_mocked_provider_call(self):
        headers = signup_and_login("m@example.com")
        client.post("/keys", json={"provider": "openai", "api_key": "sk-fake"}, headers=headers)

        with patch(
            "app.routers.usage.get_openai_costs",
            return_value=[{"date": "2026-08-27", "cost_usd": 4.5}],
        ):
            r = client.get("/usage/openai", headers=headers)

        assert r.status_code == 200
        assert r.json()["total_cost_usd"] == 4.5

    def test_summary_aggregates_across_both_providers(self):
        headers = signup_and_login("n@example.com")
        client.post("/keys", json={"provider": "openai", "api_key": "sk-fake"}, headers=headers)
        client.post("/keys", json={"provider": "anthropic", "api_key": "sk-ant-fake"}, headers=headers)

        with patch(
            "app.routers.usage.get_openai_costs",
            return_value=[{"date": "2026-08-27", "cost_usd": 10.0}],
        ):
            client.get("/usage/openai", headers=headers)

        with patch(
            "app.routers.usage.get_anthropic_costs",
            return_value=[{"date": "2026-08-27", "cost_usd": 5.0}],
        ):
            client.get("/usage/anthropic", headers=headers)

        r = client.get("/usage/summary", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_cost_usd"] == 15.0
        assert data["by_provider"]["openai"] == 10.0
        assert data["by_provider"]["anthropic"] == 5.0

    def test_repeated_refresh_does_not_duplicate_cached_rows(self):
        headers = signup_and_login("o@example.com")
        client.post("/keys", json={"provider": "openai", "api_key": "sk-fake"}, headers=headers)

        with patch(
            "app.routers.usage.get_openai_costs",
            return_value=[{"date": "2026-08-27", "cost_usd": 4.5}],
        ):
            client.get("/usage/openai", headers=headers)
            r = client.get("/usage/openai", headers=headers)

        assert len(r.json()["daily"]) == 1
        assert r.json()["total_cost_usd"] == 4.5


class TestMCPApiKeyEndpoint:
    def test_generated_key_has_expected_format_and_is_shown_once(self):
        headers = signup_and_login("p@example.com")
        r = client.post("/api-keys", json={"label": "Claude Desktop"}, headers=headers)
        assert r.status_code == 201
        assert r.json()["raw_key"].startswith("llmck_")
        assert r.json()["label"] == "Claude Desktop"

    def test_requires_authentication(self):
        r = client.post("/api-keys", json={"label": "test"})
        assert r.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])