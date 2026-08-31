import re
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from datetime import datetime


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must include a lowercase letter.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must include an uppercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must include a number.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must include a special character.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    created_at: datetime


class ProviderKeyCreate(BaseModel):
    provider: str
    api_key: str


class ProviderKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider: str
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    label: str | None = None


class ApiKeyCreateResponse(BaseModel):
    id: int
    raw_key: str
    label: str | None