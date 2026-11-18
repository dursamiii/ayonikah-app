from datetime import date

from fastapi.testclient import TestClient

from backend.database import reset_database
from backend.main import app


client = TestClient(app)


def setup_function():
    reset_database()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_list_update_and_delete_item():
    payload = {
        "title": "Book venue",
        "category": "venue",
        "status": "todo",
        "event_date": "2026-06-20",
        "notes": "Ask about outdoor space",
        "image_url": "https://example.com/venue.jpg",
    }
    created = client.post("/api/plans", json=payload)
    assert created.status_code == 201
    item = created.json()
    assert set(item) == {
        "id", "title", "category", "status", "event_date", "notes",
        "image_url", "created_at", "updated_at",
    }
    assert item["title"] == payload["title"]
    assert item["event_date"] == payload["event_date"]
    item_id = item["id"]

    listed = client.get("/api/plans")
    assert listed.status_code == 200
    assert listed.json() == [item]

    fetched = client.get(f"/api/plans/{item_id}")
    assert fetched.status_code == 200
    assert fetched.json() == item

    updated = client.patch(
        f"/api/plans/{item_id}",
        json={"status": "done", "notes": "Contract signed"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert updated.json()["notes"] == "Contract signed"
    assert updated.json()["updated_at"] >= item["updated_at"]

    deleted = client.delete(f"/api/plans/{item_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/plans/{item_id}").status_code == 404


def test_validation_rejects_bad_status_and_missing_title():
    invalid = {
        "title": "",
        "category": "venue",
        "status": "unknown",
        "event_date": date.today().isoformat(),
    }
    response = client.post("/api/plans", json=invalid)
    assert response.status_code == 422


def test_validation_rejects_invalid_date_and_url():
    response = client.post(
        "/api/plans",
        json={
            "title": "Venue",
            "category": "venue",
            "status": "todo",
            "event_date": "not-a-date",
            "image_url": "not-a-url",
        },
    )
    assert response.status_code == 422


def test_validation_rejects_non_http_image_url():
    response = client.post(
        "/api/plans",
        json={
            "title": "Venue",
            "category": "venue",
            "image_url": "ftp://example.com/venue.jpg",
        },
    )
    assert response.status_code == 422


def test_persistence_survives_new_database_connection():
    response = client.post(
        "/api/plans",
        json={"title": "Photographer", "category": "vendor"},
    )
    assert response.status_code == 201
    item_id = response.json()["id"]

    with client as reopened_client:
        fetched = reopened_client.get(f"/api/plans/{item_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == item_id


def test_cors_allows_frontend_origin():
    response = client.options(
        "/api/plans",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_missing_item_returns_not_found():
    assert client.get("/api/plans/999999").status_code == 404
    assert client.patch("/api/plans/999999", json={"status": "done"}).status_code == 404
    assert client.delete("/api/plans/999999").status_code == 404
