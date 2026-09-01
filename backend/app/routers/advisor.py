from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UsageRecord
from app.routers.auth import get_current_user
from app.agents.pattern_finder import find_patterns
from app.agents.recommender import generate_recommendation

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.get("")
def get_advice(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(UsageRecord).filter(UsageRecord.user_id == current_user.id).all()
    usage_dicts = [{"provider": r.provider, "cost_usd": r.cost_usd, "tokens": r.tokens or 0} for r in records]

    pattern = find_patterns(usage_dicts)
    recommendation = generate_recommendation(pattern)

    return {"pattern": pattern, "recommendation": recommendation}