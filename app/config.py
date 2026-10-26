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


settings = Settings()
