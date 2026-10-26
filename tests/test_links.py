"""API tests for Phase 1 link creation and resolution."""

import pytest


def test_create_link(client):
    response = client.post("/api/links", json={"long_url": "https://example.com/a"})

    assert response.status_code == 201
    body = response.json()
    assert body["long_url"] == "https://example.com/a"
    assert 6 <= len(body["code"]) <= 8
    assert body["short_url"] == f"https://short.example/{body['code']}"


def test_redirects_to_original_url(client):
    create_response = client.post("/api/links", json={"long_url": "https://example.com/redirect"})
    code = create_response.json()["code"]

    response = client.get(f"/{code}")

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/redirect"


def test_unknown_code_returns_404(client):
    response = client.get("/missing")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "localhost",
        "http://localhost:3000/",
        "http://127.0.0.1:8080/",
        "http://10.0.0.1/internal",
        "http://172.16.0.1/internal",
        "http://192.168.1.1/internal",
        "http://[::1]/internal",
        "https://short.example/already-shortener",
        "https://api.short.example/already-shortener",
    ],
)
def test_rejects_unsafe_or_invalid_url(client, url):
    response = client.post("/api/links", json={"long_url": url})

    assert response.status_code == 422
