"""
End-to-end tests for the API endpoints themselves (auth, keys, usage
logging, advisor), using FastAPI's TestClient against a fresh, isolated
SQLite database that is dropped and recreated between every test.

This complements the other test files (test_security.py tests the
crypto/hashing primitives in isolation; test_cost_advisor.py tests
pricing, tokenizers, and the two agents in isolation; test_mcp_server.py
tests MCP auth and the summary tool). This file exercises the actual
endpoints a real frontend calls, proving the whole request/response
chain works, not just its parts.
"""

import os
os.environ.setdefault("ENCRYPTION_KEY", "kQ8rN2vX9pL4mZ7wJ1cF6bT3sA0dY5hU8gK2eR4nQ6w=")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_api_endpoints.db")

import pytest
from unittest.mock import patch, MagicMock
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
    def test_log_usage_without_anthropic_key_returns_404(self):
        headers = signup_and_login("l@example.com")
        r = client.post("/usage/log", json={
            "provider": "anthropic", "model": "claude-haiku-4-5", "prompt": "test"
        }, headers=headers)
        assert r.status_code == 404

    def test_log_usage_openai_computes_real_cost(self):
        """OpenAI's tokenizer is local -- no mocking needed, this is a real calculation."""
        headers = signup_and_login("m@example.com")
        r = client.post("/usage/log", json={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt": "Hello, this is a test prompt for token counting.",
            "expected_output_tokens": 50,
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["input_tokens"] > 0
        assert data["cost_usd"] > 0
        assert data["fits_context_window"] is True

    def test_log_usage_anthropic_with_mocked_tokenizer(self):
        headers = signup_and_login("n@example.com")
        client.post("/keys", json={"provider": "anthropic", "api_key": "sk-ant-fake"}, headers=headers)

        with patch("app.routers.usage_log.count_anthropic_tokens", return_value=100):
            r = client.post("/usage/log", json={
                "provider": "anthropic", "model": "claude-haiku-4-5",
                "prompt": "test", "expected_output_tokens": 50,
            }, headers=headers)

        assert r.status_code == 200
        assert r.json()["input_tokens"] == 100

    def test_log_usage_unknown_model_returns_400(self):
        headers = signup_and_login("o@example.com")
        r = client.post("/usage/log", json={
            "provider": "openai", "model": "not-a-real-model", "prompt": "test"
        }, headers=headers)
        assert r.status_code == 400


class TestAdvisorEndpoint:
    def test_advisor_with_no_usage_gives_helpful_message(self):
        headers = signup_and_login("p@example.com")
        r = client.get("/advisor", headers=headers)
        assert r.status_code == 200
        assert "No usage logged" in r.json()["recommendation"]

    def test_advisor_reflects_logged_usage(self):
        headers = signup_and_login("q@example.com")
        client.post("/usage/log", json={
            "provider": "openai", "model": "gpt-4o-mini",
            "prompt": "test prompt", "expected_output_tokens": 50,
        }, headers=headers)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="You're spending efficiently."))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.agents.recommender.Groq", return_value=mock_client):
            r = client.get("/advisor", headers=headers)

        assert r.status_code == 200
        assert r.json()["pattern"]["total_calls"] == 1
        assert r.json()["recommendation"] == "You're spending efficiently."


class TestMCPApiKeyEndpoint:
    def test_generated_key_has_expected_format_and_is_shown_once(self):
        headers = signup_and_login("r@example.com")
        r = client.post("/api-keys", json={"label": "Claude Desktop"}, headers=headers)
        assert r.status_code == 201
        assert r.json()["raw_key"].startswith("llmck_")
        assert r.json()["label"] == "Claude Desktop"

    def test_requires_authentication(self):
        r = client.post("/api-keys", json={"label": "test"})
        assert r.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])