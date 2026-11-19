import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from fastapi import FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from .database import get_connection, initialize_database

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", Path(__file__).resolve().parent / "uploads"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", "5242880"))
ALLOWED_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


class PlanStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class PlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    status: PlanStatus = PlanStatus.todo
    event_date: Optional[date] = None
    notes: str = Field(default="", max_length=5000)
    image_url: Optional[HttpUrl] = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    view_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "category", mode="before")
    @classmethod
    def trim_required(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class PlanUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    status: Optional[PlanStatus] = None
    event_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=5000)
    image_url: Optional[HttpUrl] = None
    custom_fields: Optional[dict[str, Any]] = None
    view_config: Optional[dict[str, Any]] = None

    @field_validator("title", "category", mode="before")
    @classmethod
    def trim_optional(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class Plan(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    category: str
    status: PlanStatus
    event_date: Optional[date]
    notes: str
    image_url: Optional[str]
    image_source: str
    custom_fields: dict[str, Any]
    view_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Ayonikah Planner API", version="1.0.0", lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR, check_dir=False), name="uploads")
origins = {"http://localhost:3000", "http://127.0.0.1:3000"}
origins.update(filter(None, (value.strip() for value in os.environ.get("CORS_ORIGINS", "").split(","))))
app.add_middleware(CORSMiddleware, allow_origins=sorted(origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def error(code: str, message: str, fields: Optional[dict[str, list[str]]] = None, http_status: int = 400) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return JSONResponse(status_code=http_status, content={"error": body})


@app.exception_handler(RequestValidationError)
def validation_exception(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields: dict[str, list[str]] = {}
    for item in exc.errors():
        location = item.get("loc", ())
        name = str(location[-1]) if location else "request"
        fields.setdefault(name, []).append(item.get("msg", "Invalid value"))
    return error("validation_error", "Request validation failed", fields, 422)


@app.exception_handler(HTTPException)
def http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    mapping = {404: "not_found", 409: "conflict", 413: "payload_too_large", 415: "unsupported_media_type"}
    code = mapping.get(exc.status_code, "validation_error" if exc.status_code == 422 else "internal_error")
    return error(code, str(exc.detail), http_status=exc.status_code)


def now() -> datetime:
    return datetime.now(timezone.utc)


def row_to_plan(row: sqlite3.Row) -> Plan:
    values = dict(row)
    for field in ("custom_fields", "view_config"):
        try:
            values[field] = json.loads(values[field] or "{}")
        except (TypeError, json.JSONDecodeError):
            values[field] = {}
    values["image_source"] = values.get("image_source") or ("url" if values.get("image_url") else "none")
    return Plan.model_validate(values)


def find_plan(plan_id: int):
    with get_connection() as connection:
        return connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/plans", response_model=list[Plan])
@app.get("/api/items", response_model=list[Plan])
def list_plans(status_filter: Optional[PlanStatus] = Query(default=None, alias="status")) -> list[Plan]:
    query = "SELECT * FROM plans"
    params: tuple[str, ...] = ()
    if status_filter is not None:
        query += " WHERE status = ?"
        params = (status_filter.value,)
    query += " ORDER BY event_date IS NULL, event_date, id"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [row_to_plan(row) for row in rows]


@app.post("/api/plans", response_model=Plan, status_code=201)
@app.post("/api/items", response_model=Plan, status_code=201)
def create_plan(payload: PlanCreate) -> Plan:
    timestamp = now().isoformat()
    values = (payload.title, payload.category, payload.status.value, payload.event_date.isoformat() if payload.event_date else None, payload.notes, str(payload.image_url) if payload.image_url else None, "url" if payload.image_url else "none", json.dumps(payload.custom_fields), json.dumps(payload.view_config), timestamp, timestamp)
    with get_connection() as connection:
        cursor = connection.execute("INSERT INTO plans (title, category, status, event_date, notes, image_url, image_source, custom_fields, view_config, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
        row = connection.execute("SELECT * FROM plans WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_plan(row)


@app.get("/api/plans/{plan_id}", response_model=Plan)
@app.get("/api/items/{plan_id}", response_model=Plan)
def get_plan(plan_id: int) -> Plan:
    row = find_plan(plan_id)
    if row is None:
        raise HTTPException(404, "Plan not found")
    return row_to_plan(row)


@app.patch("/api/plans/{plan_id}", response_model=Plan)
@app.patch("/api/items/{plan_id}", response_model=Plan)
def update_plan(plan_id: int, payload: PlanUpdate) -> Plan:
    if find_plan(plan_id) is None:
        raise HTTPException(404, "Plan not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return get_plan(plan_id)
    if "title" in changes and not changes["title"]:
        raise HTTPException(422, "title cannot be blank")
    if "category" in changes and not changes["category"]:
        raise HTTPException(422, "category cannot be blank")
    for field in ("status",):
        if field in changes and changes[field] is not None:
            changes[field] = changes[field].value
    if "event_date" in changes and changes["event_date"] is not None:
        changes["event_date"] = changes["event_date"].isoformat()
    if "image_url" in changes:
        changes["image_url"] = str(changes["image_url"]) if changes["image_url"] else None
        changes["image_source"] = "url" if changes["image_url"] else "none"
    for field in ("custom_fields", "view_config"):
        if field in changes:
            changes[field] = json.dumps(changes[field])
    changes["updated_at"] = now().isoformat()
    assignments = ", ".join(f"{key} = ?" for key in changes)
    with get_connection() as connection:
        connection.execute(f"UPDATE plans SET {assignments} WHERE id = ?", (*changes.values(), plan_id))
        row = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return row_to_plan(row)


@app.delete("/api/plans/{plan_id}", status_code=204)
@app.delete("/api/items/{plan_id}", status_code=204)
def delete_plan(plan_id: int) -> Response:
    row = find_plan(plan_id)
    if row is None:
        raise HTTPException(404, "Plan not found")
    with get_connection() as connection:
        connection.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    if row["image_source"] == "upload" and row["image_url"]:
        (UPLOAD_DIR / Path(row["image_url"]).name).unlink(missing_ok=True)
    return Response(status_code=204)


@app.post("/api/plans/{plan_id}/image", response_model=Plan)
def upload_image(plan_id: int, file: UploadFile = File(...)) -> Plan:
    row = find_plan(plan_id)
    if row is None:
        raise HTTPException(404, "Plan not found")
    suffix = ALLOWED_MIME.get(file.content_type or "")
    if suffix is None:
        raise HTTPException(415, "Unsupported image type")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image exceeds maximum size")
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = UPLOAD_DIR / filename
    target.write_bytes(data)
    old_path = UPLOAD_DIR / Path(row["image_url"]).name if row["image_source"] == "upload" and row["image_url"] else None
    timestamp = now().isoformat()
    try:
        with get_connection() as connection:
            connection.execute("UPDATE plans SET image_url = ?, image_source = 'upload', updated_at = ? WHERE id = ?", (f"/uploads/{filename}", timestamp, plan_id))
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if old_path:
        old_path.unlink(missing_ok=True)
    return get_plan(plan_id)


@app.delete("/api/plans/{plan_id}/image", status_code=204)
def delete_image(plan_id: int) -> Response:
    row = find_plan(plan_id)
    if row is None:
        raise HTTPException(404, "Plan not found")
    if row["image_source"] == "upload" and row["image_url"]:
        (UPLOAD_DIR / Path(row["image_url"]).name).unlink(missing_ok=True)
    with get_connection() as connection:
        connection.execute("UPDATE plans SET image_url = NULL, image_source = 'none', updated_at = ? WHERE id = ?", (now().isoformat(), plan_id))
    return Response(status_code=204)
