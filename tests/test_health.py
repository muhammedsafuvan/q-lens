
from unittest.mock import MagicMock

import redis
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.internal import health
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/internal/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "queuelens-api",
    }


def test_readiness_check_healthy(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection

    redis_client = MagicMock()

    monkeypatch.setattr(
        health.engine,
        "connect",
        lambda: connection,
    )
    monkeypatch.setattr(
        health.redis.Redis,
        "from_url",
        lambda *args, **kwargs: redis_client,
    )

    response = client.get("/internal/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "queuelens-api",
        "dependencies": {
            "postgres": "healthy",
            "redis": "healthy",
        },
    }

    redis_client.ping.assert_called_once()
    redis_client.close.assert_called_once()


def test_readiness_check_postgres_unhealthy(monkeypatch):
    redis_client = MagicMock()

    monkeypatch.setattr(
        health.engine,
        "connect",
        lambda: (_ for _ in ()).throw(SQLAlchemyError("Database unavailable")),
    )
    monkeypatch.setattr(
        health.redis.Redis,
        "from_url",
        lambda *args, **kwargs: redis_client,
    )

    response = client.get("/internal/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["dependencies"] == {
        "postgres": "unhealthy",
        "redis": "healthy",
    }


def test_readiness_check_redis_unhealthy(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection

    redis_client = MagicMock()
    redis_client.ping.side_effect = redis.ConnectionError(
        "Redis unavailable"
    )

    monkeypatch.setattr(
        health.engine,
        "connect",
        lambda: connection,
    )
    monkeypatch.setattr(
        health.redis.Redis,
        "from_url",
        lambda *args, **kwargs: redis_client,
    )

    response = client.get("/internal/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["dependencies"] == {
        "postgres": "healthy",
        "redis": "unhealthy",
    }

    redis_client.close.assert_called_once()
