from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import engine
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "queuelens-api",
    }


def test_readiness_check_healthy(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection

    monkeypatch.setattr(
        engine,
        "connect",
        lambda: connection,
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "queuelens-api",
        "dependencies": {"postgres": "healthy"},
    }


def test_readiness_check_postgres_unhealthy(monkeypatch):
    monkeypatch.setattr(
        engine,
        "connect",
        lambda: (_ for _ in ()).throw(
            SQLAlchemyError("Database unavailable")
        ),
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "unhealthy",
        "service": "queuelens-api",
        "dependencies": {"postgres": "unhealthy"},
    }
