import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings


def _get_jwt_secret() -> str:
    settings = get_settings()
    secret = settings.jwt_secret_key

    if not secret or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured with at least 32 characters."
        )

    return secret


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
) -> tuple[str, int]:
    settings = get_settings()

    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_access_token_minutes)

    payload = {
        "sub": str(user_id),
        "email": email,
        "workspace_id": str(workspace_id),
        "sid": str(session_id),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }

    token = jwt.encode(
        payload,
        _get_jwt_secret(),
        algorithm="HS256",
    )

    return token, settings.jwt_access_token_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()

    payload = jwt.decode(
        token,
        _get_jwt_secret(),
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={
            "require": [
                "sub",
                "email",
                "workspace_id",
                "sid",
                "iss",
                "aud",
                "iat",
                "exp",
                "jti",
                "token_type",
            ]
        },
    )

    if payload.get("token_type") != "access":
        raise jwt.InvalidTokenError("Invalid token type.")

    return payload
