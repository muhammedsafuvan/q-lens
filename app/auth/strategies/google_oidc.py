import secrets
from typing import Any

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status
from starlette.responses import RedirectResponse

from app.auth.interfaces.authentication_strategy import AuthenticationStrategy
from app.core.config import get_settings


class GoogleOIDCStrategy(AuthenticationStrategy):
    """Google OpenID Connect authentication strategy."""

    @property
    def provider(self) -> str:
        return "google"

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.google_client_id or not settings.google_client_secret:
            raise RuntimeError("Google OAuth credentials are not configured.")

        self.oauth = OAuth()

        self.oauth.register(
            name="google",
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            client_kwargs={
                "scope": "openid email profile",
            },
        )

    async def authorization_redirect(
        self,
        request: Request,
        redirect_uri: str,
    ) -> RedirectResponse:
        nonce = secrets.token_urlsafe(32)

        return await self.oauth.google.authorize_redirect(
            request,
            redirect_uri,
            nonce=nonce,
        )

    async def authenticate_callback(
        self,
        request: Request,
    ) -> dict[str, Any]:
        try:
            token = await self.oauth.google.authorize_access_token(request)
        except OAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authentication failed.",
            ) from exc

        userinfo = token.get("userinfo")

        if not userinfo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google did not return a verified identity.",
            )

        identity = dict(userinfo)

        if not identity.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google identity is missing its subject identifier.",
            )

        if not identity.get("email"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google account does not have an email address.",
            )

        if identity.get("email_verified") is not True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Google email address is not verified.",
            )

        return {
            "provider": self.provider,
            "provider_subject": identity["sub"],
            "email": identity["email"],
            "email_verified": True,
            "name": identity.get("name") or identity["email"],
            "avatar_url": identity.get("picture"),
        }
