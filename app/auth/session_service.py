import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.token_service import create_access_token
from app.core.config import get_settings
from app.models import RefreshToken, User, WorkspaceMember


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_refresh_token_record(
    db: Session,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
) -> tuple[str, RefreshToken]:
    settings = get_settings()

    raw_token = secrets.token_urlsafe(64)

    record = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
    )

    db.add(record)
    db.flush()

    return raw_token, record


def create_session(
    db: Session,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    family_id = uuid.uuid4()

    try:
        with db.begin():
            # Serialize logins and refreshes for this user.
            user = db.scalar(select(User).where(User.id == user_id).with_for_update())

            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is unavailable.",
                )

            membership = db.scalar(
                select(WorkspaceMember).where(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.workspace_id == workspace_id,
                )
            )

            if membership is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not belong to this workspace.",
                )

            # Revoke every previous session belonging to this user.
            db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )

            access_token, expires_in = create_access_token(
                user_id=user.id,
                email=user.email,
                workspace_id=workspace_id,
                session_id=family_id,
            )

            raw_refresh_token, _ = _create_refresh_token_record(
                db,
                user_id,
                family_id,
            )

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }

    except Exception:
        db.rollback()
        raise


def rotate_refresh_token(
    db: Session,
    raw_refresh_token: str,
) -> dict[str, Any]:
    token_hash = hash_refresh_token(raw_refresh_token)

    error: str | None = None
    response: dict[str, Any] | None = None

    try:
        with db.begin():
            # Initial lookup identifies which user's row must be locked.
            candidate = db.scalar(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )

            if candidate is None:
                error = "invalid"

            else:
                # Use the same lock order as create_session().
                user = db.scalar(
                    select(User).where(User.id == candidate.user_id).with_for_update()
                )

                # Re-read and lock the refresh token after locking the user.
                old_record = db.scalar(
                    select(RefreshToken)
                    .where(RefreshToken.token_hash == token_hash)
                    .with_for_update()
                )

                if old_record is None:
                    error = "invalid"

                else:
                    now = datetime.now(UTC)

                    if old_record.revoked_at is not None:
                        # Reuse detected: revoke the entire session family.
                        db.execute(
                            update(RefreshToken)
                            .where(
                                RefreshToken.family_id == old_record.family_id,
                                RefreshToken.revoked_at.is_(None),
                            )
                            .values(revoked_at=now)
                        )
                        error = "reuse"

                    elif old_record.expires_at <= now:
                        # Expiry invalidates the whole session family.
                        db.execute(
                            update(RefreshToken)
                            .where(
                                RefreshToken.family_id == old_record.family_id,
                                RefreshToken.revoked_at.is_(None),
                            )
                            .values(revoked_at=now)
                        )
                        error = "expired"

                    elif user is None or not user.is_active:
                        db.execute(
                            update(RefreshToken)
                            .where(
                                RefreshToken.family_id == old_record.family_id,
                                RefreshToken.revoked_at.is_(None),
                            )
                            .values(revoked_at=now)
                        )
                        error = "user_unavailable"

                    else:
                        membership = db.scalar(
                            select(WorkspaceMember)
                            .where(WorkspaceMember.user_id == user.id)
                            .order_by(WorkspaceMember.created_at.asc())
                            .limit(1)
                        )

                        if membership is None:
                            db.execute(
                                update(RefreshToken)
                                .where(
                                    RefreshToken.family_id == old_record.family_id,
                                    RefreshToken.revoked_at.is_(None),
                                )
                                .values(revoked_at=now)
                            )
                            error = "user_unavailable"

                        else:
                            access_token, expires_in = create_access_token(
                                user_id=user.id,
                                email=user.email,
                                workspace_id=membership.workspace_id,
                                session_id=old_record.family_id,
                            )

                            new_refresh_token, new_record = (
                                _create_refresh_token_record(
                                    db,
                                    user.id,
                                    old_record.family_id,
                                )
                            )

                            old_record.revoked_at = now
                            old_record.replaced_by_token_id = new_record.id

                            response = {
                                "access_token": access_token,
                                "refresh_token": new_refresh_token,
                                "token_type": "Bearer",
                                "expires_in": expires_in,
                            }

        # Raise after the transaction commits so revocations persist.
        if error == "reuse":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected. Please sign in again.",
            )

        if error == "user_unavailable":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is unavailable.",
            )

        if error == "expired":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired.",
            )

        if error == "invalid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        if response is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to refresh session.",
            )

        return response

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise


def revoke_refresh_token(
    db: Session,
    raw_refresh_token: str,
) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)

    try:
        with db.begin():
            candidate = db.scalar(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )

            if candidate is None:
                return

            db.scalar(
                select(User).where(User.id == candidate.user_id).with_for_update()
            )

            record = db.scalar(
                select(RefreshToken)
                .where(RefreshToken.token_hash == token_hash)
                .with_for_update()
            )

            if record is None:
                return

            now = datetime.now(UTC)

            db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == record.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )

    except Exception:
        db.rollback()
        raise
