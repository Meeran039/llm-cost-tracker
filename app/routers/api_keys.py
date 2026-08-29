from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiKey
from app.schemas import ApiKeyCreateRequest, ApiKeyCreateResponse
from app.security import generate_mcp_api_key, hash_mcp_api_key
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api-keys", tags=["mcp-api-keys"])


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    req: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates a new API key for use with the MCP server. The raw key is
    returned here ONCE -- only its hash is stored, so it can never be
    retrieved again after this response. If lost, the user must create
    a new one.
    """
    raw_key = generate_mcp_api_key()
    key_row = ApiKey(
        user_id=current_user.id,
        hashed_key=hash_mcp_api_key(raw_key),
        label=req.label,
    )
    db.add(key_row)
    db.commit()
    db.refresh(key_row)

    return ApiKeyCreateResponse(id=key_row.id, raw_key=raw_key, label=key_row.label)