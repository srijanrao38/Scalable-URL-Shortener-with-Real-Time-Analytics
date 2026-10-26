"""Shared test fixtures using an isolated in-memory database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.config import settings
from app.db import Base, get_db
from app.main import app


class IsolatedRedis:
    """Small in-memory Redis fake with state isolated to one test client."""

    def __init__(self):
        self.values = {}
        self.lists = {}
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

    def ping(self):
        return True

    def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)


@pytest.fixture()
def client(monkeypatch):
    # Keep ordinary API tests independent from Redis state left by other
    # tests. Tests that exercise Redis failures or rate-limit behavior replace
    # this fake with their own client using monkeypatch.
    monkeypatch.setattr(main, "redis_client", IsolatedRedis())

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    original_base_url = settings.base_url
    settings.base_url = "https://short.example"
    with TestClient(app, follow_redirects=False) as test_client:
        test_client.testing_session_factory = TestingSessionLocal
        yield test_client
    settings.base_url = original_base_url
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
