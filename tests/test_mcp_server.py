"""
Tests the MCP authentication path and the get_usage_summary tool.
Uses a fresh SQLite file per test run via conftest-less setup (env vars
are set before any app module is imported, matching the pattern used
in test_security.py).
"""

import os
os.environ.setdefault("ENCRYPTION_KEY", "kQ8rN2vX9pL4mZ7wJ1cF6bT3sA0dY5hU8gK2eR4nQ6w=")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_mcp.db")

import pytest
from datetime import datetime, timezone

from app.database import Base, engine, SessionLocal
from app.models import User, ApiKey, UsageRecord
from app.security import hash_password, generate_mcp_api_key, hash_mcp_api_key, authenticate_mcp_api_key
from app.mcp_server import get_usage_summary


@pytest.fixture(autouse=True)
def fresh_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user_with_api_key(db):
    user = User(email="mcp-test@example.com", hashed_password=hash_password("testpass123"))
    db.add(user)
    db.commit()
    db.refresh(user)

    raw_key = generate_mcp_api_key()
    key_row = ApiKey(user_id=user.id, hashed_key=hash_mcp_api_key(raw_key), label="test key")
    db.add(key_row)
    db.commit()

    return user, raw_key


class TestMCPAuthentication:
    def test_valid_key_resolves_to_correct_user(self, db, user_with_api_key):
        user, raw_key = user_with_api_key
        found_user = authenticate_mcp_api_key(db, raw_key)
        assert found_user is not None
        assert found_user.id == user.id

    def test_invalid_key_returns_none(self, db, user_with_api_key):
        found_user = authenticate_mcp_api_key(db, "llmck_totally_wrong_key")
        assert found_user is None

    def test_key_only_resolves_to_its_own_user_not_others(self, db):
        user_a = User(email="a@example.com", hashed_password=hash_password("passA"))
        user_b = User(email="b@example.com", hashed_password=hash_password("passB"))
        db.add_all([user_a, user_b])
        db.commit()

        raw_key_a = generate_mcp_api_key()
        db.add(ApiKey(user_id=user_a.id, hashed_key=hash_mcp_api_key(raw_key_a)))
        db.commit()

        found_user = authenticate_mcp_api_key(db, raw_key_a)
        assert found_user.id == user_a.id
        assert found_user.id != user_b.id


class TestUsageSummaryTool:
    def test_returns_correct_total_for_valid_key(self, db, user_with_api_key):
        user, raw_key = user_with_api_key
        db.add(UsageRecord(
            user_id=user.id, provider="openai",
            date=datetime.now(timezone.utc), cost_usd=10.0,
        ))
        db.add(UsageRecord(
            user_id=user.id, provider="anthropic",
            date=datetime.now(timezone.utc), cost_usd=5.5,
        ))
        db.commit()

        result = get_usage_summary(api_key=raw_key, days=30)
        assert "15.5" in result
        assert "openai" in result
        assert "anthropic" in result

    def test_invalid_key_gives_clear_message(self, db):
        result = get_usage_summary(api_key="llmck_wrong", days=30)
        assert "Invalid API key" in result

    def test_no_usage_data_gives_clear_message(self, db, user_with_api_key):
        _, raw_key = user_with_api_key
        result = get_usage_summary(api_key=raw_key, days=30)
        assert "No usage data found" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])