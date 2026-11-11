import json
import uuid
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
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
from app.models.workspace_member import WorkspaceMember
from app.schemas.auth import (
    CurrentUserResponse,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_frontend_origin(frontend_url: str) -> str:
    """
    Extract and validate the frontend origin used by postMessage.
    """
    parsed_url = urlsplit(frontend_url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise RuntimeError("FRONTEND_URL must be a valid HTTP or HTTPS URL.")

    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def _oauth_popup_response(
    *,
    frontend_url: str,
    message_type: str,
    payload: dict[str, Any],
) -> HTMLResponse:
    """
    Send the OAuth result to the frontend window that opened the popup.
    """
    frontend_origin = _get_frontend_origin(frontend_url)

    message = json.dumps(payload).replace("<", "\\u003c")

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>QLens Authentication</title>
      </head>
      <body>
        <p>Completing QLens authentication...</p>

        <script>
          (() => {{
            const message = {{
              type: {json.dumps(message_type)},
              payload: {message}
            }};

            if (window.opener) {{
              window.opener.postMessage(
                message,
                {json.dumps(frontend_origin)}
              );
              window.close();
            }} else {{
              document.body.textContent =
                "Authentication completed, but the login window could not be reached. Please close this window and try again.";
            }}
          }})();
        </script>
      </body>
    </html>
    """

    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _oauth_popup_error(message: str) -> HTMLResponse:
    """
    Send an authentication error to the frontend popup opener.
    """
    settings = get_settings()

    return _oauth_popup_response(
        frontend_url=settings.frontend_url,
        message_type="QLENS_AUTH_ERROR",
        payload={"message": message},
    )


@router.get("/google/start")
async def google_login(
    request: Request,
    popup: bool = False,
) -> RedirectResponse:
    settings = get_settings()

    if not settings.session_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth session configuration is missing.",
        )

    service = get_authentication_service()

    if popup:
        request.session["qlens_oauth_popup"] = True

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


@router.get("/google/callback", response_model=None)
async def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any] | HTMLResponse:
    popup_mode = bool(request.session.get("qlens_oauth_popup"))

    if "error" in request.query_params:
        request.session.pop("qlens_oauth_popup", None)

        if popup_mode:
            return _oauth_popup_error("Google authentication was cancelled or denied.")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication was cancelled or denied.",
        )

    if not request.session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth session is missing or expired.",
        )

    # Remove only our popup flag. Authlib's OAuth state and nonce
    # remain available for callback validation.
    request.session.pop("qlens_oauth_popup", None)

    service = get_authentication_service()

    try:
        identity = await service.authenticate_callback(
            provider="google",
            request=request,
        )
    except RuntimeError as exc:
        if popup_mode:
            return _oauth_popup_error("Google authentication is not configured.")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        ) from exc
    except HTTPException:
        if popup_mode:
            return _oauth_popup_error("Google authentication failed. Please try again.")

        raise

    try:
        account = provision_google_user(db, identity)

        token_pair = create_session(
            db=db,
            user_id=uuid.UUID(account["user_id"]),
            workspace_id=uuid.UUID(account["workspace_id"]),
        )
    except Exception:
        if popup_mode:
            return _oauth_popup_error(
                "We could not complete your QLens account setup. Please try again."
            )

        raise

    payload = {
        "message": "Google authentication successful.",
        "account": account,
        **token_pair,
    }

    if popup_mode:
        settings = get_settings()

        return _oauth_popup_response(
            frontend_url=settings.frontend_url,
            message_type="QLENS_AUTH_SUCCESS",
            payload=payload,
        )

    # Preserve the original JSON response for Swagger and API clients.
    return payload


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(
    payload: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return rotate_refresh_token(db, payload.refresh_token)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    revoke_refresh_token(db, payload.refresh_token)

    return {"message": "Session revoked successfully."}


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUserResponse:
    membership = db.scalar(
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == current_user.id)
        .order_by(
            WorkspaceMember.created_at.asc(),
            WorkspaceMember.id.asc(),
        )
        .limit(1)
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any workspace",
        )

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        workspace_id=membership.workspace_id,
    )
