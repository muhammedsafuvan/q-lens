import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.workspace_dependencies import get_workspace_admin
from app.core.api_keys import generate_api_key
from app.core.config import get_settings
from app.db.session import get_db
from app.models import APIKey, User
from app.schemas.api_keys import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyResponse,
    APIKeyRevokeRequest,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/api-keys",
    tags=["Workspace API Keys"],
)


@router.post(
    "",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    workspace_id: uuid.UUID,
    payload: APIKeyCreate,
    current_user: Annotated[User, Depends(get_workspace_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    settings = get_settings()
    plaintext_key, key_hash = generate_api_key(settings.app_env)

    api_key = APIKey(
        workspace_id=workspace_id,
        created_by_user_id=current_user.id,
        name=payload.name,
        key_prefix=plaintext_key[:12],
        key_hash=key_hash,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyCreatedResponse(
        id=api_key.id,
        workspace_id=api_key.workspace_id,
        name=api_key.name,
        key=plaintext_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[APIKeyResponse])
def list_api_keys(
    workspace_id: uuid.UUID,
    _: Annotated[User, Depends(get_workspace_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return list(
        db.scalars(
            select(APIKey)
            .where(APIKey.workspace_id == workspace_id)
            .order_by(APIKey.created_at.desc())
        ).all()
    )


@router.patch(
    "/{key_id}",
    response_model=APIKeyResponse,
)
def revoke_api_key(
    workspace_id: uuid.UUID,
    key_id: uuid.UUID,
    payload: APIKeyRevokeRequest,
    _: Annotated[User, Depends(get_workspace_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    api_key = db.scalar(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.workspace_id == workspace_id,
        )
    )

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    if api_key.revoked_at is None and payload.revoked:
        api_key.revoked_at = datetime.now(UTC)
        db.commit()
        db.refresh(api_key)

    return api_key
