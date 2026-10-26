"""Redis click-queue consumer and database writer."""

import json
import logging
import os
from datetime import datetime
from typing import Any

import redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Click, Link
from app.redis_client import redis_client
from worker.user_agent import parse_user_agent


logger = logging.getLogger(__name__)


# BRPOP may legitimately wait for the full blocking timeout when the queue is
# empty, so the worker needs a socket timeout longer than that wait.
BRPOP_TIMEOUT_SECONDS = 5
WORKER_SOCKET_TIMEOUT_SECONDS = 10
worker_redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=0.2,
    socket_timeout=WORKER_SOCKET_TIMEOUT_SECONDS,
)


def _decode_event(raw_event: str | bytes) -> dict[str, Any]:
    if isinstance(raw_event, bytes):
        raw_event = raw_event.decode("utf-8")
    event = json.loads(raw_event)
    required = {"code", "timestamp", "user_agent", "ip_hash"}
    if not isinstance(event, dict) or not required.issubset(event):
        raise ValueError("click event is missing required fields")
    if not all(isinstance(event[key], str) and event[key] for key in required):
        raise ValueError("click event fields must be non-empty strings")
    return event


def _dead_letter(raw_event: str | bytes, queue) -> None:
    try:
        queue.lpush(settings.failed_click_queue_name, raw_event)
    except redis.RedisError:
        logger.exception("Could not write failed click event to dead-letter queue")


def process_event(raw_event: str | bytes, db: Session, queue=redis_client) -> bool:
    """Process one event; malformed input is skipped and DB failures are retried later."""

    try:
        event = _decode_event(raw_event)
        clicked_at = datetime.fromisoformat(event["timestamp"])
    except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Skipping malformed click event: %s", exc)
        return False

    try:
        link = db.scalar(select(Link).where(Link.code == event["code"]))
        if link is None:
            logger.warning("Skipping click event for unknown code %s", event["code"])
            return False
        device, browser = parse_user_agent(event["user_agent"])
        db.add(
            Click(
                link_id=link.id,
                clicked_at=clicked_at,
                device=device,
                browser=browser,
                ip_hash=event["ip_hash"],
            )
        )
        db.commit()
        return True
    except Exception as exc:  # DB/constraint errors must not kill the consumer.
        db.rollback()
        logger.exception("Failed to persist click event: %s", exc)
        _dead_letter(raw_event, queue)
        return False


def run_worker() -> None:
    """Continuously consume events with a timeout so the loop remains stoppable."""

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    while True:
        try:
            item = worker_redis_client.brpop(
                settings.click_queue_name,
                timeout=BRPOP_TIMEOUT_SECONDS,
            )
        except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError) as exc:
            logger.warning("Redis queue read failed; retrying: %s", exc)
            continue
        if item is None:
            continue
        _, raw_event = item
        with SessionLocal() as db:
            process_event(raw_event, db)


if __name__ == "__main__":
    run_worker()
