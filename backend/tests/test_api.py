import io
import sqlite3

from fastapi.testclient import TestClient

from backend.database import DATABASE_PATH, initialize_database, reset_database
from backend.main import UPLOAD_DIR, app

client = TestClient(app)


def setup_function():
    reset_database()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_list_update_and_delete_item():
    payload = {"title": "Book venue", "category": "venue", "status": "todo", "event_date": "2026-06-20", "notes": "Ask about outdoor space", "image_url": "https://example.com/venue.jpg"}
    created = client.post("/api/plans", json=payload)
    assert created.status_code == 201
    item = created.json()
    assert set(item) == {"id", "title", "category", "status", "event_date", "notes", "image_url", "image_source", "custom_fields", "view_config", "created_at", "updated_at"}
    assert item["title"] == payload["title"]
    assert item["event_date"] == payload["event_date"]
    item_id = item["id"]
    assert client.get("/api/plans").json() == [item]
    assert client.get(f"/api/plans/{item_id}").json() == item
    updated = client.patch(f"/api/plans/{item_id}", json={"status": "done", "notes": "Contract signed"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert updated.json()["notes"] == "Contract signed"
    assert updated.json()["updated_at"] >= item["updated_at"]
    assert client.delete(f"/api/plans/{item_id}").status_code == 204
    assert client.get(f"/api/plans/{item_id}").status_code == 404


def test_validation_and_errors_use_error_envelope():
    response = client.post("/api/plans", json={"title": "", "category": "venue", "status": "unknown"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "title" in response.json()["error"]["fields"]
    response = client.get("/api/plans/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_validation_rejects_invalid_date_and_url():
    response = client.post("/api/plans", json={"title": "Venue", "category": "venue", "event_date": "not-a-date", "image_url": "ftp://example.com/a.jpg"})
    assert response.status_code == 422


def test_create_trims_fields_and_rejects_blank_after_trim():
    response = client.post("/api/plans", json={"title": " Venue ", "category": " venue "})
    assert response.status_code == 201
    assert response.json()["title"] == "Venue"
    assert response.json()["category"] == "venue"
    assert client.post("/api/plans", json={"title": "   ", "category": "venue"}).status_code == 422


def test_alias_filter_empty_patch_and_customization():
    first = client.post("/api/items", json={"title": "One", "category": "venue"}).json()
    client.post("/api/plans", json={"title": "Two", "category": "venue", "status": "done"})
    assert len(client.get("/api/items?status=todo").json()) == 1
    assert client.patch(f"/api/items/{first['id']}", json={}).json() == first
    response = client.patch(f"/api/plans/{first['id']}", json={"custom_fields": {"budget": 120}, "view_config": {"compact": True}})
    assert response.status_code == 200
    assert response.json()["custom_fields"] == {"budget": 120}
    assert response.json()["view_config"] == {"compact": True}


def test_persistence_survives_new_database_connection():
    response = client.post("/api/plans", json={"title": "Photographer", "category": "vendor"})
    item_id = response.json()["id"]
    with client as reopened_client:
        assert reopened_client.get(f"/api/plans/{item_id}").status_code == 200


def test_startup_migrates_existing_schema_without_deleting_data():
    migration_path = DATABASE_PATH.with_name("migration-test.sqlite3")
    migration_path.unlink(missing_ok=True)
    connection = sqlite3.connect(migration_path)
    connection.execute("CREATE TABLE plans (id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, status TEXT NOT NULL, event_date TEXT, notes TEXT NOT NULL DEFAULT '', image_url TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    connection.execute("INSERT INTO plans VALUES (1, 'Old plan', 'venue', 'todo', NULL, '', 'https://example.com/old.jpg', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')")
    connection.commit()
    connection.close()
    try:
        import backend.database as database
        original = database.DATABASE_PATH
        database.DATABASE_PATH = migration_path
        initialize_database()
        with database.get_connection() as migrated:
            row = migrated.execute("SELECT title, image_source, custom_fields FROM plans WHERE id = 1").fetchone()
        assert tuple(row) == ("Old plan", "url", "{}")
        database.DATABASE_PATH = original
    finally:
        migration_path.unlink(missing_ok=True)


def test_upload_enforces_media_type_size_safe_name_and_serves_file():
    item = client.post("/api/plans", json={"title": "Venue", "category": "venue"}).json()
    unsupported = client.post(f"/api/plans/{item['id']}/image", files={"file": ("x.svg", b"<svg/>", "image/svg+xml")})
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "unsupported_media_type"
    uploaded = client.post(f"/api/plans/{item['id']}/image", files={"file": ("../../unsafe.png", b"PNG bytes", "image/png")})
    assert uploaded.status_code == 200
    plan = uploaded.json()
    assert plan["image_source"] == "upload"
    assert plan["image_url"].startswith("/uploads/")
    assert "unsafe" not in plan["image_url"]
    assert client.get(plan["image_url"]).content == b"PNG bytes"
    assert client.delete(f"/api/plans/{item['id']}/image").status_code == 204
    assert client.get(f"/api/plans/{item['id']}").json()["image_url"] is None


def test_cors_allows_frontend_origin():
    response = client.options("/api/plans", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_missing_item_returns_not_found():
    assert client.patch("/api/plans/999999", json={"status": "done"}).status_code == 404
    assert client.delete("/api/plans/999999").status_code == 404
