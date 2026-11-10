import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_authentication_service
from app.auth.dependencies import get_current_user
from app.auth.provisioning import provision_google_user
from app.auth.session_service import (
    create_session,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google/start")
async def google_login(request: Request) -> RedirectResponse:
    settings = get_settings()

    if not settings.session_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth session configuration is missing.",
        )

    service = get_authentication_service()

    try:
        return await service.authorization_redirect(
            provider="google",
            request=request,
            redirect_uri=settings.google_redirect_uri,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        ) from exc


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    if "error" in request.query_params:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication was cancelled or denied.",
        )

    if not request.session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth session is missing or expired.",
        )

    service = get_authentication_service()

    try:
        identity = await service.authenticate_callback(
            provider="google",
            request=request,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        ) from exc

    account = provision_google_user(db, identity)

    token_pair = create_session(
        db=db,
        user_id=uuid.UUID(account["user_id"]),
        workspace_id=uuid.UUID(account["workspace_id"]),
    )

    return {
        "message": "Google authentication successful.",
        "account": account,
        **token_pair,
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(
    payload: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return rotate_refresh_token(
        db,
        payload.refresh_token,
    )


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    revoke_refresh_token(
        db,
        payload.refresh_token,
    )

    return {"message": "Session revoked successfully."}


@router.get("/me")
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
    }
