from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


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