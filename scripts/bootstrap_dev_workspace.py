import hashlib
import uuid

from sqlalchemy import select, update

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import APIKey, JobEvent, Workspace

WORKSPACE_NAME = "QueueLens Development"
WORKSPACE_SLUG = "queuelens-development"
API_KEY_NAME = "Local Development"


def bootstrap() -> None:
    settings = get_settings()
    plaintext_key = settings.queuelens_api_key
    key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()

    with SessionLocal() as db:
        workspace = db.scalar(select(Workspace).where(Workspace.slug == WORKSPACE_SLUG))

        if workspace is None:
            workspace = Workspace(
                id=uuid.uuid4(),
                name=WORKSPACE_NAME,
                slug=WORKSPACE_SLUG,
            )
            db.add(workspace)
            db.flush()

        api_key = db.scalar(
            select(APIKey).where(
                APIKey.workspace_id == workspace.id,
                APIKey.name == API_KEY_NAME,
                APIKey.revoked_at.is_(None),
            )
        )

        if api_key is None:
            api_key = APIKey(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                name=API_KEY_NAME,
                key_prefix=plaintext_key[:12],
                key_hash=key_hash,
            )
            db.add(api_key)
        else:
            api_key.key_prefix = plaintext_key[:12]
            api_key.key_hash = key_hash

        backfill_result = db.execute(
            update(JobEvent)
            .where(JobEvent.workspace_id.is_(None))
            .values(workspace_id=workspace.id)
        )

        backfilled_count = backfill_result.rowcount or 0

        db.commit()

        print("QueueLens development workspace ready.")
        print(f"Workspace ID: {workspace.id}")
        print(f"Backfilled events: {backfilled_count}")
        print("Development API key configured successfully.")


if __name__ == "__main__":
    bootstrap()
