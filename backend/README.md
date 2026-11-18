# Planner API

FastAPI + SQLite backend for planner records.

## Run

From repository root:

```sh
python3 -m pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --reload
```

SQLite database defaults to `backend/planner.sqlite3`; SQLite creates it on startup. Do not check database file into source control. API docs: `http://127.0.0.1:8000/docs`.

## API

- `GET /health` → `{ "status": "ok" }`
- `GET /api/plans` → records ordered by event date; optional `?status=todo|in_progress|done`
- `POST /api/plans` → create record (`201`)
- `GET /api/plans/{id}` → one record (`404` when absent)
- `PATCH /api/plans/{id}` → update supplied fields (`404` when absent)
- `DELETE /api/plans/{id}` → `204` (`404` when absent)

JSON record fields: `id`, `title`, `category`, `status`, `event_date`, `notes`, `image_url`, `created_at`, `updated_at`. `event_date` is an ISO date or `null`; timestamps are UTC ISO-8601. `status` values: `todo`, `in_progress`, `done`. `title` and `category` required on create; optional `notes` defaults to empty string. `image_url` must be HTTP(S) URL or null. Invalid input returns `422`.

CORS allows `http://localhost:3000` and `http://127.0.0.1:3000`. Change origins through app configuration before using another frontend origin.

## Tests

```sh
python3 -m pytest backend/tests -q
```
