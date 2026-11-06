
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.job_event import JobEvent as JobEventModel

EVENT_IDS = [
    uuid.UUID("11111111-1111-4111-8111-111111111111"),
    uuid.UUID("22222222-2222-4222-8222-222222222222"),
]

INGESTION_URL = "/internal/v1/events/batch"


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db

    settings = get_settings()

    with TestClient(
        app,
        headers={
            "Authorization": f"Bearer {settings.queuelens_api_key}",
        },
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def cleanup_test_events():
    def cleanup():
        with SessionLocal() as db:
            db.execute(
                delete(JobEventModel).where(JobEventModel.event_id.in_(EVENT_IDS))
            )
            db.commit()

    cleanup()
    yield
    cleanup()


def get_payload():
    return {
        "events": [
            {
                "event_id": str(EVENT_IDS[0]),
                "task_id": "test-task-001",
                "task_name": "queuelens.demo.process",
                "event_type": "started",
                "worker_name": "worker-1",
                "queue_name": "default",
                "attempt": 1,
            },
            {
                "event_id": str(EVENT_IDS[1]),
                "task_id": "test-task-001",
                "task_name": "queuelens.demo.process",
                "event_type": "succeeded",
                "worker_name": "worker-1",
                "queue_name": "default",
                "attempt": 1,
            },
        ]
    }


def test_ingest_events_successfully(client):
    response = client.post(
        INGESTION_URL,
        json=get_payload(),
    )

    assert response.status_code == 202
    assert response.json() == {
        "accepted_count": 2,
        "duplicate_count": 0,
    }


def test_ingest_duplicate_events(client):
    payload = get_payload()

    first_response = client.post(INGESTION_URL, json=payload)
    second_response = client.post(INGESTION_URL, json=payload)

    assert first_response.status_code == 202
    assert first_response.json()["accepted_count"] == 2

    assert second_response.status_code == 202
    assert second_response.json() == {
        "accepted_count": 0,
        "duplicate_count": 2,
    }

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count())
            .select_from(JobEventModel)
            .where(JobEventModel.event_id.in_(EVENT_IDS))
        )

    assert count == 2


def test_ingest_rejects_empty_batch(client):
    response = client.post(
        INGESTION_URL,
        json={"events": []},
    )

    assert response.status_code == 422


def test_ingest_rejects_invalid_event_type(client):
    payload = get_payload()
    payload["events"][0]["event_type"] = "unknown"

    response = client.post(
        INGESTION_URL,
        json=payload,
    )

    assert response.status_code == 422


def test_ingest_rejects_missing_api_key():
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as unauthenticated_client:
            response = unauthenticated_client.post(
                INGESTION_URL,
                json=get_payload(),
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
