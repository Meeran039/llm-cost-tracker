from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ProviderKey, UsageRecord
from app.security import decrypt_provider_key
from app.routers.auth import get_current_user
from app.pricing import calculate_cost, fits_context_window, UnknownModelError
from app.tokenizers.openai_tokenizer import count_openai_tokens
from app.tokenizers.anthropic_tokenizer import count_anthropic_tokens, AnthropicTokenizerError

router = APIRouter(prefix="/usage", tags=["usage"])


class LogUsageRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    expected_output_tokens: int = 0


class LogUsageResponse(BaseModel):
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    fits_context_window: bool


def _get_input_tokens(provider: str, model: str, prompt: str, db: Session, user_id: int) -> int:
    if provider == "openai":
        return count_openai_tokens(model, prompt)

    if provider == "anthropic":
        key_row = (
            db.query(ProviderKey)
            .filter(ProviderKey.user_id == user_id, ProviderKey.provider == "anthropic")
            .first()
        )
        if not key_row:
            raise HTTPException(
                status_code=404,
                detail="No Anthropic key connected. Add your regular API key via POST /keys first.",
            )
        api_key = decrypt_provider_key(key_row.encrypted_key)
        try:
            return count_anthropic_tokens(api_key, model, prompt)
        except AnthropicTokenizerError as e:
            raise HTTPException(status_code=401, detail=str(e))

    raise HTTPException(status_code=400, detail="provider must be 'openai' or 'anthropic'")


@router.post("/log", response_model=LogUsageResponse)
def log_usage(
    req: LogUsageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        input_tokens = _get_input_tokens(req.provider, req.model, req.prompt, db, current_user.id)
        total_tokens = input_tokens + req.expected_output_tokens
        cost = calculate_cost(req.model, input_tokens, req.expected_output_tokens)
        within_window = fits_context_window(req.model, total_tokens)
    except UnknownModelError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.add(UsageRecord(
        user_id=current_user.id,
        provider=req.provider,
        date=datetime.now(timezone.utc),
        cost_usd=cost,
        tokens=total_tokens,
    ))
    db.commit()

    return LogUsageResponse(
        provider=req.provider,
        model=req.model,
        input_tokens=input_tokens,
        output_tokens=req.expected_output_tokens,
        cost_usd=cost,
        fits_context_window=within_window,
    )