import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def _get_fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not set. Generate one with generate_encryption_key().")
    return Fernet(settings.ENCRYPTION_KEY.encode())


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode()


def encrypt_provider_key(plaintext_key: str) -> str:
    return _get_fernet().encrypt(plaintext_key.encode()).decode()


def decrypt_provider_key(encrypted_key: str) -> str:
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except InvalidToken:
        raise ValueError("Could not decrypt provider key. It may be corrupted.")


JWT_ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise ValueError("Invalid or expired token")


def generate_mcp_api_key() -> str:
    return f"llmck_{secrets.token_urlsafe(32)}"


def hash_mcp_api_key(raw_key: str) -> str:
    return _pwd_context.hash(raw_key)


def verify_mcp_api_key(raw_key: str, hashed_key: str) -> bool:
    return _pwd_context.verify(raw_key, hashed_key)
def authenticate_mcp_api_key(db, raw_key: str):
    """
    Looks up which user (if any) owns this raw MCP API key.

    NOTE: this checks the key against every stored hash (O(n) in number
    of issued keys), which is fine at portfolio scale but would need an
    indexed lookup (e.g. a non-secret key prefix stored alongside the
    hash) to scale to many users/keys in a real production system.
    """
    from app.models import ApiKey, User  # local import avoids a circular import at module load

    for key_row in db.query(ApiKey).all():
        if verify_mcp_api_key(raw_key, key_row.hashed_key):
            return db.query(User).filter(User.id == key_row.user_id).first()
    return None