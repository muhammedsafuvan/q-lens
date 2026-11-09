import hashlib
import secrets
import uuid

from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.models import APIKey, JobEvent, Workspace

WORKSPACE_NAME = "QueueLens Development"
WORKSPACE_SLUG = "queuelens-development"
API_KEY_NAME = "Local Development"
API_KEY_PREFIX = "ql_test_"


def generate_api_key() -> tuple[str, str]:
    secret = secrets.token_urlsafe(32)
    plaintext_key = f"{API_KEY_PREFIX}{secret}"
    key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
    return plaintext_key, key_hash


def bootstrap() -> None:
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

        plaintext_key = None

        if api_key is None:
            plaintext_key, key_hash = generate_api_key()

            api_key = APIKey(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                name=API_KEY_NAME,
                key_prefix=plaintext_key[:12],
                key_hash=key_hash,
            )
            db.add(api_key)

        backfill_result = db.execute(
            update(JobEvent)
            .where(JobEvent.workspace_id.is_(None))
            .values(workspace_id=workspace.id)
        )

        backfilled_count = backfill_result.rowcount or 0

        db.commit()

        print("\nQueueLens development workspace ready.")
        print(f"Workspace ID: {workspace.id}")
        print(f"Backfilled events: {backfilled_count}")

        if plaintext_key:
            print("\nNEW API KEY (save it now; it cannot be retrieved later):")
            print(plaintext_key)
        else:
            print("\nAn active development API key already exists.")
            print("The existing plaintext key cannot be recovered.")


if __name__ == "__main__":
    bootstrap()
