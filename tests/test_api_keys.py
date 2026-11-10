import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.auth.dependencies import get_current_user
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models import APIKey, User, Workspace, WorkspaceMember

API_KEYS_URL = "/api/v1/workspaces/{workspace_id}/api-keys"


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def workspace_context():
    unique_id = uuid.uuid4().hex[:12]

    with SessionLocal() as db:
        user = User(
            email=f"api-key-test-{unique_id}@example.com",
            name="API Key Test User",
        )

        workspace = Workspace(
            name="API Key Test Workspace",
            slug=f"api-key-test-{unique_id}",
        )

        db.add_all([user, workspace])
        db.flush()

        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )

        db.add(membership)
        db.commit()

        context = {
            "user": user,
            "workspace_id": workspace.id,
            "membership_id": membership.id,
        }

    yield context

    with SessionLocal() as db:
        db.execute(delete(APIKey).where(APIKey.workspace_id == context["workspace_id"]))
        db.execute(
            delete(WorkspaceMember).where(
                WorkspaceMember.id == context["membership_id"]
            )
        )
        db.execute(delete(Workspace).where(Workspace.id == context["workspace_id"]))
        db.execute(delete(User).where(User.id == context["user"].id))
        db.commit()


@pytest.fixture
def client(workspace_context):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: workspace_context["user"]

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_key(client, workspace_id):
    return client.post(
        API_KEYS_URL.format(workspace_id=workspace_id),
        json={"name": "Production SDK"},
    )


def test_create_api_key(client, workspace_context):
    response = create_key(
        client,
        workspace_context["workspace_id"],
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Production SDK"
    assert data["workspace_id"] == str(workspace_context["workspace_id"])
    assert data["key"]
    assert data["key_prefix"] == data["key"][:12]

    with SessionLocal() as db:
        api_key = db.get(APIKey, uuid.UUID(data["id"]))

        assert api_key is not None
        assert api_key.created_by_user_id == workspace_context["user"].id
        assert api_key.key_hash == hashlib.sha256(data["key"].encode()).hexdigest()
        assert api_key.key_hash != data["key"]


def test_list_api_keys_does_not_expose_secret(client, workspace_context):
    create_response = create_key(
        client,
        workspace_context["workspace_id"],
    )

    assert create_response.status_code == 201

    response = client.get(
        API_KEYS_URL.format(workspace_id=workspace_context["workspace_id"])
    )

    assert response.status_code == 200

    keys = response.json()

    assert len(keys) == 1
    assert keys[0]["name"] == "Production SDK"
    assert keys[0]["key_prefix"]
    assert "key" not in keys[0]
    assert "key_hash" not in keys[0]


def test_workspace_member_cannot_manage_api_keys(
    client,
    workspace_context,
):
    with SessionLocal() as db:
        membership = db.get(
            WorkspaceMember,
            workspace_context["membership_id"],
        )
        membership.role = "member"
        db.commit()

    response = create_key(
        client,
        workspace_context["workspace_id"],
    )

    assert response.status_code == 403


def test_user_cannot_access_another_workspace(client):
    another_workspace_id = uuid.uuid4()

    response = client.get(API_KEYS_URL.format(workspace_id=another_workspace_id))

    assert response.status_code == 404


def test_revoke_api_key(client, workspace_context):
    create_response = create_key(
        client,
        workspace_context["workspace_id"],
    )

    assert create_response.status_code == 201

    created_key = create_response.json()

    response = client.patch(
        (API_KEYS_URL + "/{key_id}").format(
            workspace_id=workspace_context["workspace_id"],
            key_id=created_key["id"],
        ),
        json={"revoked": True},
    )

    assert response.status_code == 200
    assert response.json()["revoked_at"] is not None

    with SessionLocal() as db:
        api_key = db.get(APIKey, uuid.UUID(created_key["id"]))
        assert api_key.revoked_at is not None


def test_revoked_api_key_cannot_ingest_events(
    client,
    workspace_context,
):
    create_response = create_key(
        client,
        workspace_context["workspace_id"],
    )

    assert create_response.status_code == 201

    created_key = create_response.json()

    revoke_response = client.patch(
        (API_KEYS_URL + "/{key_id}").format(
            workspace_id=workspace_context["workspace_id"],
            key_id=created_key["id"],
        ),
        json={"revoked": True},
    )

    assert revoke_response.status_code == 200

    ingestion_response = client.post(
        "/api/v1/events/batch",
        headers={
            "Authorization": f"Bearer {created_key['key']}",
        },
        json={
            "events": [
                {
                    "event_id": str(uuid.uuid4()),
                    "task_id": "revoked-key-test",
                    "task_name": "tests.revoked_key",
                    "event_type": "started",
                }
            ]
        },
    )

    assert ingestion_response.status_code == 401


def test_revoke_api_key_from_another_workspace_returns_404(
    client,
    workspace_context,
):
    create_response = create_key(
        client,
        workspace_context["workspace_id"],
    )

    created_key = create_response.json()

    response = client.patch(
        (API_KEYS_URL + "/{key_id}").format(
            workspace_id=uuid.uuid4(),
            key_id=created_key["id"],
        ),
        json={"revoked": True},
    )

    assert response.status_code == 404


def test_api_key_name_cannot_be_empty(client, workspace_context):
    response = client.post(
        API_KEYS_URL.format(workspace_id=workspace_context["workspace_id"]),
        json={"name": "   "},
    )

    assert response.status_code == 422
