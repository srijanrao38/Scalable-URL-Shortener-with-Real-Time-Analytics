"""Tests for redirect event enqueueing and worker behavior."""

import json
from datetime import datetime, timezone

import redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.db import Base
from app.models import Click, Link
from worker.worker import process_event


class QueueRedis:
    def __init__(self, fail_lpush=False):
        self.values = {}
        self.lists = {}
        self.expirations = {}
        self.counts = {}
        self.fail_lpush = fail_lpush

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.expirations[key] = ttl

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, ttl):
        self.expirations[key] = ttl

    def ttl(self, key):
        return 60

    def lpush(self, key, value):
        if self.fail_lpush:
            raise redis.ConnectionError("queue unavailable")
        self.lists.setdefault(key, []).insert(0, value)


def _sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_redirect_enqueues_hashed_click_event(client, monkeypatch):
    queue = QueueRedis()
    monkeypatch.setattr(main, "redis_client", queue)
    created = client.post("/api/links", json={"long_url": "https://example.com/click"}).json()

    response = client.get(
        f"/{created['code']}",
        headers={"user-agent": "Mozilla/5.0", "x-forwarded-for": "203.0.113.10"},
    )

    assert response.status_code == 302
    event = json.loads(queue.lists[main.settings.click_queue_name][0])
    assert event["code"] == created["code"]
    assert event["user_agent"] == "Mozilla/5.0"
    assert event["ip_hash"] != "203.0.113.10"
    assert len(event["ip_hash"]) == 64


def test_redirect_succeeds_when_click_enqueue_fails(client, monkeypatch):
    queue = QueueRedis(fail_lpush=True)
    monkeypatch.setattr(main, "redis_client", queue)
    created = client.post("/api/links", json={"long_url": "https://example.com/no-loss"}).json()

    response = client.get(f"/{created['code']}")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/no-loss"


def test_worker_processes_valid_event():
    engine, db = _sqlite_session()
    try:
        link = Link(code="worker1", long_url="https://example.com")
        db.add(link)
        db.commit()
        event = json.dumps(
            {
                "code": "worker1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                "ip_hash": "a" * 64,
            }
        )

        assert process_event(event, db, QueueRedis()) is True
        click = db.scalar(select(Click))
        assert click is not None
        assert click.device == "mobile"
        assert click.browser == "Safari"
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_worker_skips_malformed_event():
    class NoDatabaseUse:
        def scalar(self, query):
            raise AssertionError("malformed events must not query the database")

    assert process_event("{not-json", NoDatabaseUse(), QueueRedis()) is False


def test_worker_dead_letters_database_failure():
    class FailingDatabase:
        def scalar(self, query):
            return Link(id=1, code="failed1", long_url="https://example.com")

        def add(self, value):
            pass

        def commit(self):
            raise RuntimeError("database unavailable")

        def rollback(self):
            pass

    queue = QueueRedis()
    event = json.dumps(
        {
            "code": "failed1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_agent": "curl/8.0",
            "ip_hash": "b" * 64,
        }
    )

    assert process_event(event, FailingDatabase(), queue) is False
    assert queue.lists[main.settings.failed_click_queue_name] == [event]
