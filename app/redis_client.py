"""Shared Redis client used for cache and rate-limiting operations."""

import redis

from app.config import settings


# Short timeouts keep the API's fail-open paths responsive when Redis is down.
redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=0.2,
    socket_timeout=0.2,
)
