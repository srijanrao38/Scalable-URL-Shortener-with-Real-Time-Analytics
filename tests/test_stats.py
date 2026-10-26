"""Seeded tests for link listing and each analytics aggregation endpoint."""

from datetime import datetime, timedelta, timezone

from app.models import Click, Link


def seed_link_and_clicks(client):
    created = client.post("/api/links", json={"long_url": "https://example.com/stats"}).json()
    db = client.testing_session_factory()
    link = db.query(Link).filter_by(code=created["code"]).one()
    now = datetime.now(timezone.utc)
    db.add_all(
        [
            Click(link_id=link.id, clicked_at=now, device="desktop", browser="Chrome", ip_hash="a" * 64),
            Click(link_id=link.id, clicked_at=now - timedelta(days=1), device="mobile", browser="Safari", ip_hash="b" * 64),
            Click(link_id=link.id, clicked_at=now - timedelta(days=2), device="desktop", browser="Chrome", ip_hash="c" * 64),
            Click(link_id=link.id, clicked_at=now - timedelta(days=45), device="bot", browser="curl", ip_hash="d" * 64),
        ]
    )
    db.commit()
    db.close()
    return created["code"]


def test_stats_summary_aggregates_seeded_clicks(client):
    code = seed_link_and_clicks(client)

    response = client.get(f"/api/links/{code}/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_clicks"] == 4
    assert sum(item["clicks"] for item in body["clicks_per_day"]) == 3
    assert {item["name"]: item["count"] for item in body["device_breakdown"]} == {"desktop": 2, "mobile": 1, "bot": 1}
    assert {item["name"]: item["count"] for item in body["browser_breakdown"]} == {"Chrome": 2, "Safari": 1, "curl": 1}


def test_total_stats_endpoint(client):
    code = seed_link_and_clicks(client)
    response = client.get(f"/api/links/{code}/stats/total")
    assert response.json() == {"code": code, "total_clicks": 4}


def test_daily_stats_endpoint(client):
    code = seed_link_and_clicks(client)
    response = client.get(f"/api/links/{code}/stats/daily")
    assert response.status_code == 200
    assert sum(item["clicks"] for item in response.json()) == 3


def test_device_stats_endpoint(client):
    code = seed_link_and_clicks(client)
    response = client.get(f"/api/links/{code}/stats/devices")
    assert response.status_code == 200
    assert {item["name"]: item["count"] for item in response.json()}["mobile"] == 1


def test_browser_stats_endpoint(client):
    code = seed_link_and_clicks(client)
    response = client.get(f"/api/links/{code}/stats/browsers")
    assert response.status_code == 200
    assert {item["name"]: item["count"] for item in response.json()}["Chrome"] == 2


def test_list_links_includes_click_count(client):
    code = seed_link_and_clicks(client)
    response = client.get("/api/links")
    assert response.status_code == 200
    assert response.json()[0]["code"] == code
    assert response.json()[0]["click_count"] == 4


def test_cors_allows_configured_frontend_origin(client):
    response = client.options(
        "/api/links",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
