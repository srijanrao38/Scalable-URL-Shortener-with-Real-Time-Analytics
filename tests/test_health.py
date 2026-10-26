"""Health endpoint tests."""

import redis

from app import main


def test_health_reports_postgres_and_redis(client, monkeypatch):
    class HealthyRedis:
        def ping(self):
            return True

    monkeypatch.setattr(main, "redis_client", HealthyRedis())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "postgres": "ok", "redis": "ok"}


def test_health_returns_503_when_redis_is_unavailable(client, monkeypatch):
    class DownRedis:
        def ping(self):
            raise redis.ConnectionError("down")

    monkeypatch.setattr(main, "redis_client", DownRedis())
    response = client.get("/health")
    assert response.status_code == 503
