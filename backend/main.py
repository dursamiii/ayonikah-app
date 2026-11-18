from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from enum import Enum
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from .database import get_connection, initialize_database


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
    image_url: Optional[AnyHttpUrl] = None


class PlanUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    status: Optional[PlanStatus] = None
    event_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=5000)
    image_url: Optional[AnyHttpUrl] = None


class Plan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    status: PlanStatus
    event_date: Optional[date]
    notes: str
    image_url: Optional[AnyHttpUrl]
    created_at: datetime
    updated_at: datetime


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="Ayonikah Planner API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now() -> datetime:
    return datetime.now(timezone.utc)


def row_to_plan(row) -> Plan:
    return Plan.model_validate(dict(row))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/plans", response_model=list[Plan])
@app.get("/api/items", response_model=list[Plan])
def list_plans(
    status_filter: Optional[PlanStatus] = Query(default=None, alias="status"),
) -> list[Plan]:
    query = "SELECT * FROM plans"
    params: tuple[str, ...] = ()
    if status_filter is not None:
        query += " WHERE status = ?"
        params = (status_filter.value,)
    query += " ORDER BY event_date IS NULL, event_date, id"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [row_to_plan(row) for row in rows]


@app.post("/api/plans", response_model=Plan, status_code=status.HTTP_201_CREATED)
@app.post("/api/items", response_model=Plan, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate) -> Plan:
    timestamp = now().isoformat()
    values = (
        payload.title.strip(), payload.category.strip(), payload.status.value,
        payload.event_date.isoformat() if payload.event_date else None,
        payload.notes, str(payload.image_url) if payload.image_url else None,
        timestamp, timestamp,
    )
    if not values[0] or not values[1]:
        raise HTTPException(status_code=422, detail="title and category cannot be blank")
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO plans
            (title, category, status, event_date, notes, image_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", values,
        )
        row = connection.execute("SELECT * FROM plans WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_plan(row)


@app.get("/api/plans/{plan_id}", response_model=Plan)
@app.get("/api/items/{plan_id}", response_model=Plan)
def get_plan(plan_id: int) -> Plan:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return row_to_plan(row)


@app.patch("/api/plans/{plan_id}", response_model=Plan)
@app.patch("/api/items/{plan_id}", response_model=Plan)
def update_plan(plan_id: int, payload: PlanUpdate) -> Plan:
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes:
        changes["title"] = changes["title"].strip()
        if not changes["title"]:
            raise HTTPException(status_code=422, detail="title cannot be blank")
    if "category" in changes:
        changes["category"] = changes["category"].strip()
        if not changes["category"]:
            raise HTTPException(status_code=422, detail="category cannot be blank")
    if "status" in changes:
        changes["status"] = changes["status"].value
    if "event_date" in changes and changes["event_date"] is not None:
        changes["event_date"] = changes["event_date"].isoformat()
    if "image_url" in changes and changes["image_url"] is not None:
        changes["image_url"] = str(changes["image_url"])
    if not changes:
        return get_plan(plan_id)
    changes["updated_at"] = now().isoformat()
    assignments = ", ".join(f"{key} = ?" for key in changes)
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE plans SET {assignments} WHERE id = ?",
            (*changes.values(), plan_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Plan not found")
        row = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return row_to_plan(row)


@app.delete("/api/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
@app.delete("/api/items/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
