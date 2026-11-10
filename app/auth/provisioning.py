import re
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, UserIdentity, Workspace, WorkspaceMember


def _generate_workspace_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    base = base or "workspace"

    return f"{base[:60]}-{uuid.uuid4().hex[:12]}"


def _create_default_workspace(db: Session, user: User) -> Workspace:
    workspace = Workspace(
        id=uuid.uuid4(),
        name=f"{user.name}'s Workspace"[:120],
        slug=_generate_workspace_slug(user.name),
    )

    db.add(workspace)
    db.flush()

    membership = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )

    db.add(membership)
    db.flush()

    return workspace


def _get_or_create_default_workspace(
    db: Session,
    user: User,
) -> Workspace:
    workspace = db.scalar(
        select(Workspace)
        .join(
            WorkspaceMember,
            WorkspaceMember.workspace_id == Workspace.id,
        )
        .where(WorkspaceMember.user_id == user.id)
        .order_by(
            WorkspaceMember.created_at.asc(),
            WorkspaceMember.id.asc(),
        )
        .limit(1)
    )

    if workspace is None:
        workspace = _create_default_workspace(db, user)

    return workspace


def _provision_user(
    db: Session,
    identity: dict[str, Any],
) -> dict[str, Any]:
    provider = identity["provider"]
    provider_subject = identity["provider_subject"]
    email = identity["email"].strip().lower()
    name = identity["name"].strip()[:120] or email
    avatar_url = identity.get("avatar_url")

    if provider != "google" or identity.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A verified Google identity is required.",
        )

    existing_identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == provider,
            UserIdentity.provider_subject == provider_subject,
        )
    )

    if existing_identity:
        user = db.get(User, existing_identity.user_id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The linked user account could not be found.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is disabled.",
            )

        conflicting_user = db.scalar(
            select(User).where(
                func.lower(User.email) == email,
                User.id != user.id,
            )
        )

        if conflicting_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is associated with another QLens account.",
            )

        user.email = email
        user.name = name
        user.avatar_url = avatar_url

        existing_identity.email = email
        existing_identity.email_verified = True

        workspace = _get_or_create_default_workspace(db, user)

        return {
            "user_id": str(user.id),
            "email": user.email,
            "name": user.name,
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "workspace_slug": workspace.slug,
            "is_new_user": False,
        }

    existing_user = db.scalar(select(User).where(func.lower(User.email) == email))

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An account with this email already exists. "
                "Sign in using its existing authentication method."
            ),
        )

    user = User(
        id=uuid.uuid4(),
        email=email,
        name=name,
        avatar_url=avatar_url,
        is_active=True,
    )

    db.add(user)
    db.flush()

    user_identity = UserIdentity(
        id=uuid.uuid4(),
        user_id=user.id,
        provider=provider,
        provider_subject=provider_subject,
        email=email,
        email_verified=True,
    )

    db.add(user_identity)

    workspace = _create_default_workspace(db, user)

    db.flush()

    return {
        "user_id": str(user.id),
        "email": user.email,
        "name": user.name,
        "workspace_id": str(workspace.id),
        "workspace_name": workspace.name,
        "workspace_slug": workspace.slug,
        "is_new_user": True,
    }


def provision_google_user(
    db: Session,
    identity: dict[str, Any],
) -> dict[str, Any]:
    try:
        with db.begin():
            return _provision_user(db, identity)

    except IntegrityError as exc:
        db.rollback()

        # Handle concurrent first-time login requests.
        with db.begin():
            existing_identity = db.scalar(
                select(UserIdentity).where(
                    UserIdentity.provider == identity["provider"],
                    UserIdentity.provider_subject == identity["provider_subject"],
                )
            )

            if existing_identity:
                user = db.get(User, existing_identity.user_id)

                if user is None or not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="The linked account is unavailable.",
                    )

                workspace = _get_or_create_default_workspace(db, user)

                return {
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "workspace_id": str(workspace.id),
                    "workspace_name": workspace.name,
                    "workspace_slug": workspace.slug,
                    "is_new_user": False,
                }

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to provision this account. Please try again.",
        ) from exc
