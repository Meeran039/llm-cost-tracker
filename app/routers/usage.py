from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ProviderKey, UsageRecord
from app.security import decrypt_provider_key
from app.routers.auth import get_current_user
from app.providers.openai_client import get_openai_costs, OpenAIAdminKeyError, OpenAIAPIError
from app.providers.anthropic_client import get_anthropic_costs, AnthropicAdminKeyError, AnthropicAPIError

router = APIRouter(prefix="/usage", tags=["usage"])


def _get_provider_key_or_404(db: Session, user_id: int, provider: str) -> ProviderKey:
    key_row = (
        db.query(ProviderKey)
        .filter(ProviderKey.user_id == user_id, ProviderKey.provider == provider)
        .first()
    )
    if not key_row:
        raise HTTPException(
            status_code=404,
            detail=f"No {provider} key connected. Add one via POST /keys first.",
        )
    return key_row


def _save_daily_costs(db: Session, user_id: int, provider: str, daily_costs: list[dict]) -> None:
    for entry in daily_costs:
        record_date = datetime.strptime(entry["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        existing = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.user_id == user_id,
                UsageRecord.provider == provider,
                UsageRecord.date == record_date,
            )
            .first()
        )
        if existing:
            existing.cost_usd = entry["cost_usd"]
        else:
            db.add(UsageRecord(
                user_id=user_id,
                provider=provider,
                date=record_date,
                cost_usd=entry["cost_usd"],
            ))
    db.commit()


@router.get("/openai")
def get_openai_usage(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key_row = _get_provider_key_or_404(db, current_user.id, "openai")
    admin_key = decrypt_provider_key(key_row.encrypted_key)
    start_time = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        daily_costs = get_openai_costs(admin_api_key=admin_key, start_time=start_time)
    except OpenAIAdminKeyError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except OpenAIAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _save_daily_costs(db, current_user.id, "openai", daily_costs)
    total_cost = round(sum(e["cost_usd"] for e in daily_costs), 6)

    return {"provider": "openai", "days": days, "total_cost_usd": total_cost, "daily": daily_costs}


@router.get("/anthropic")
def get_anthropic_usage(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key_row = _get_provider_key_or_404(db, current_user.id, "anthropic")
    admin_key = decrypt_provider_key(key_row.encrypted_key)
    start_time = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        daily_costs = get_anthropic_costs(admin_api_key=admin_key, start_time=start_time)
    except AnthropicAdminKeyError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except AnthropicAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _save_daily_costs(db, current_user.id, "anthropic", daily_costs)
    total_cost = round(sum(e["cost_usd"] for e in daily_costs), 6)

    return {"provider": "anthropic", "days": days, "total_cost_usd": total_cost, "daily": daily_costs}
@router.get("/summary")
def get_usage_summary(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Aggregates already-cached usage_records across all connected providers.
    Reads from cache only -- it does NOT call the provider APIs directly.
    Call GET /usage/openai and/or GET /usage/anthropic first (or let the
    frontend call them) to refresh the cache before viewing this summary.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == current_user.id, UsageRecord.date >= cutoff)
        .order_by(UsageRecord.date)
        .all()
    )

    by_provider: dict[str, float] = {}
    daily: dict[str, dict[str, float]] = {}

    for r in records:
        date_str = r.date.strftime("%Y-%m-%d")
        by_provider[r.provider] = round(by_provider.get(r.provider, 0.0) + r.cost_usd, 6)
        daily.setdefault(date_str, {})[r.provider] = r.cost_usd

    daily_combined = []
    for date_str in sorted(daily.keys()):
        entry = {"date": date_str, **daily[date_str]}
        entry["total"] = round(sum(v for k, v in daily[date_str].items() if k != "date"), 6)
        daily_combined.append(entry)

    total_cost_usd = round(sum(by_provider.values()), 6)

    return {
        "days": days,
        "total_cost_usd": total_cost_usd,
        "by_provider": by_provider,
        "daily_combined": daily_combined,
    }