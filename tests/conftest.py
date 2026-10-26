"""Shared test fixtures using an isolated in-memory database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client():
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
