# Planner API contract

Version: `1.0`

## Planner item

JSON uses snake_case. API field mapping:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `id` | integer | response only | Stable SQLite identifier. |
| `title` | string | create | 1–200 characters after trimming. |
| `category` | string | create | 1–100 characters after trimming. |
| `status` | string | no | `todo`, `in_progress`, or `done`; defaults to `todo`. |
| `event_date` | string or null | no | ISO-8601 calendar date (`YYYY-MM-DD`) or `null`. UI label: Date. |
| `notes` | string | no | Maximum 5,000 characters; defaults to empty string. |
| `image_url` | string or null | no | HTTP(S) URL or `null`. UI label: Image URL. |
| `created_at` | string | response only | UTC ISO-8601 timestamp. |
| `updated_at` | string | response only | UTC ISO-8601 timestamp; changes on update. |

Example response:

```json
{
  "id": 1,
  "title": "Book venue",
  "category": "Venue",
  "status": "todo",
  "event_date": "2026-06-20",
  "notes": "Confirm capacity and deposit.",
  "image_url": "https://example.com/venue.jpg",
  "created_at": "2026-01-01T12:00:00+00:00",
  "updated_at": "2026-01-01T12:00:00+00:00"
}
```

## Endpoints

- `GET /health` — health response `{ "status": "ok" }`.
- `GET /api/plans?status=<status>` — list items, optional status filter.
- `POST /api/plans` — create item; returns `201` and item.
- `GET /api/plans/{id}` — fetch item; `404` when absent.
- `PATCH /api/plans/{id}` — update supplied fields; returns item.
- `DELETE /api/plans/{id}` — delete item; returns `204`.

`/api/items` aliases exist for list/create/read/update/delete compatibility. Invalid payloads return `422`; missing IDs return `404`.

## Local integration

Frontend default API base: `http://localhost:8000`. Development CORS origins: `http://localhost:3000`, `http://127.0.0.1:3000`. Keep origin allowlist explicit.
