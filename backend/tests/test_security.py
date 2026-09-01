import os
import pytest

os.environ.setdefault("ENCRYPTION_KEY", "kQ8rN2vX9pL4mZ7wJ1cF6bT3sA0dY5hU8gK2eR4nQ6w=")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-not-for-production")

from app.security import (
    hash_password, verify_password,
    encrypt_provider_key, decrypt_provider_key,
    create_access_token, decode_access_token,
    generate_mcp_api_key, hash_mcp_api_key, verify_mcp_api_key,
)


class TestPasswordHashing:
    def test_correct_password_verifies(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert not verify_password("wrong-password", hashed)

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("my-secret-password")
        assert hashed != "my-secret-password"


class TestProviderKeyEncryption:
    def test_round_trip_returns_original(self):
        original = "sk-test-fake-openai-key-1234567890"
        encrypted = encrypt_provider_key(original)
        assert encrypted != original
        assert decrypt_provider_key(encrypted) == original

    def test_encrypted_value_is_not_readable(self):
        original = "sk-ant-fake-anthropic-key-abcdefg"
        encrypted = encrypt_provider_key(original)
        assert "fake-anthropic-key" not in encrypted

    def test_corrupted_ciphertext_raises_clear_error(self):
        with pytest.raises(ValueError):
            decrypt_provider_key("not-a-real-encrypted-value")


class TestJWTSessionTokens:
    def test_token_decodes_to_correct_user_id(self):
        token = create_access_token(user_id=42)
        assert decode_access_token(token) == 42

    def test_garbage_token_raises(self):
        with pytest.raises(ValueError):
            decode_access_token("not.a.real.jwt")


class TestMCPApiKeys:
    def test_generated_key_has_expected_prefix(self):
        key = generate_mcp_api_key()
        assert key.startswith("llmck_")

    def test_correct_key_verifies_against_its_hash(self):
        raw = generate_mcp_api_key()
        hashed = hash_mcp_api_key(raw)
        assert verify_mcp_api_key(raw, hashed)

    def test_wrong_key_fails_verification(self):
        raw = generate_mcp_api_key()
        hashed = hash_mcp_api_key(raw)
        assert not verify_mcp_api_key("llmck_wrong_key_entirely", hashed)