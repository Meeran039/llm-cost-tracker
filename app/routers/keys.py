from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ProviderKey
from app.schemas import ProviderKeyCreate, ProviderKeyOut
from app.security import encrypt_provider_key
from app.routers.auth import get_current_user

router = APIRouter(prefix="/keys", tags=["provider-keys"])

VALID_PROVIDERS = {"openai", "anthropic", "groq"}


@router.post("", response_model=ProviderKeyOut, status_code=status.HTTP_201_CREATED)
def add_provider_key(
    req: ProviderKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"provider must be one of {sorted(VALID_PROVIDERS)}")

    existing = (
        db.query(ProviderKey)
        .filter(ProviderKey.user_id == current_user.id, ProviderKey.provider == req.provider)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"{req.provider} key already connected, delete it first to replace")

    key_row = ProviderKey(
        user_id=current_user.id,
        provider=req.provider,
        encrypted_key=encrypt_provider_key(req.api_key),
    )
    db.add(key_row)
    db.commit()
    db.refresh(key_row)
    return key_row


@router.get("", response_model=list[ProviderKeyOut])
def list_provider_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ProviderKey).filter(ProviderKey.user_id == current_user.id).all()


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_key(key_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key_row = (
        db.query(ProviderKey)
        .filter(ProviderKey.id == key_id, ProviderKey.user_id == current_user.id)
        .first()
    )
    if not key_row:
        raise HTTPException(status_code=404, detail="Provider key not found")

    db.delete(key_row)
    db.commit()