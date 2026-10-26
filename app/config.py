"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://shortener:shortener@localhost:5432/shortener",
    )
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    trusted_proxy_ips: str = os.getenv("TRUSTED_PROXY_IPS", "127.0.0.1,::1")
    ip_hash_salt: str = os.getenv("IP_HASH_SALT", "change-me-in-production")
    click_queue_name: str = os.getenv("CLICK_QUEUE_NAME", "click_events")
    failed_click_queue_name: str = os.getenv("FAILED_CLICK_QUEUE_NAME", "click_events_failed")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost")


settings = Settings()
