import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Workspace


def test_workspace_can_be_created_and_retrieved():
    slug = f"test-{uuid.uuid4().hex[:12]}"

    with SessionLocal() as db:
        workspace = Workspace(
            name="Test Workspace",
            slug=slug,
        )

        db.add(workspace)
        db.commit()

        workspace_id = workspace.id

        result = db.scalar(select(Workspace).where(Workspace.id == workspace_id))

        assert result is not None
        assert result.name == "Test Workspace"
        assert result.slug == slug

        db.delete(result)
        db.commit()
