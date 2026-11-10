import uuid

from sqlalchemy import select

from app.core.api_keys import generate_api_key
from app.db.session import SessionLocal
from app.models import APIKey, Workspace

WORKSPACE_NAME = "QueueLens Production"
WORKSPACE_SLUG = "queuelens-production"
API_KEY_NAME = "Production SDK"


def bootstrap() -> None:
    plaintext_key = None

    with SessionLocal() as db:
        try:
            workspace = db.scalar(
                select(Workspace).where(Workspace.slug == WORKSPACE_SLUG)
            )

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
                plaintext_key, key_hash = generate_api_key("production")

                api_key = APIKey(
                    id=uuid.uuid4(),
                    workspace_id=workspace.id,
                    name=API_KEY_NAME,
                    key_prefix=plaintext_key[:12],
                    key_hash=key_hash,
                )
                db.add(api_key)

            db.commit()

            print("\nQueueLens production workspace ready.")
            print(f"Workspace ID: {workspace.id}")

            if plaintext_key:
                print("\nNEW PRODUCTION API KEY")
                print("Save it securely. It cannot be retrieved later:")
                print(plaintext_key)
            else:
                print("\nAn active production API key already exists.")
                print("The existing plaintext key cannot be recovered.")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    bootstrap()
