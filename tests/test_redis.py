"""Tests for Redis caching, rate limiting, and trusted proxy behavior."""

import redis

from app import main
from app.config import settings


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}
        self.increments = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.expirations[key] = ttl

    def incr(self, key):
        self.increments[key] = self.increments.get(key, 0) + 1
        return self.increments[key]

    def expire(self, key, ttl):
        self.expirations[key] = ttl

    def ttl(self, key):
        return settings.rate_limit_window_seconds


class DownRedis:
    def get(self, key):
        raise redis.ConnectionError("Redis is down")

    def setex(self, key, ttl, value):
        raise redis.ConnectionError("Redis is down")

    def incr(self, key):
        raise redis.ConnectionError("Redis is down")


def test_cache_miss_reads_db_and_populates_cache(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(main, "redis_client", fake)
    created = client.post("/api/links", json={"long_url": "https://example.com/miss"}).json()

    response = client.get(f"/{created['code']}")

    assert response.status_code == 302
    assert fake.values[f"link:{created['code']}"] == "https://example.com/miss"
    assert fake.expirations[f"link:{created['code']}"] == settings.cache_ttl_seconds


def test_cache_hit_redirects_without_database_lookup(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(main, "redis_client", fake)
    fake.values["link:cached"] = "https://example.com/cached"

    response = client.get("/cached")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/cached"


def test_rate_limit_allows_limit_then_returns_429(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(main, "redis_client", fake)
    original_limit = settings.rate_limit_per_minute
    settings.rate_limit_per_minute = 2
    try:
        responses = [
            client.post("/api/links", json={"long_url": f"https://example.com/{index}"})
            for index in range(3)
        ]
    finally:
        settings.rate_limit_per_minute = original_limit

    assert [response.status_code for response in responses] == [201, 201, 429]
    assert responses[-1].headers["retry-after"] == str(settings.rate_limit_window_seconds)


def test_redis_outage_falls_back_to_postgres_for_redirect(client, monkeypatch):
    monkeypatch.setattr(main, "redis_client", DownRedis())
    created = client.post("/api/links", json={"long_url": "https://example.com/fallback"}).json()

    response = client.get(f"/{created['code']}")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/fallback"
