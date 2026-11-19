# ayonikah-app

Wedding planner built with Next.js, FastAPI, and SQLite.

## Repository layout

- `backend/` — FastAPI service, SQLite persistence, API tests.
- `frontend/` — Next.js application.
- `docs/API_CONTRACT.md` — shared planner item JSON contract and endpoints.
- `docs/TECHNICAL_SPEC.md` — architecture, data model, image flow, UX/accessibility, integration boundaries, acceptance criteria, and test strategy.

## Docker Compose

Requirements: Docker Desktop with Compose v2.

```sh
cp .env.example .env
# Edit .env only when frontend must call a different API URL.
docker compose config
docker compose build
docker compose up
```

Open `http://localhost:3000`. API docs: `http://localhost:8000/docs`. Backend health: `http://localhost:8000/health`.

Compose binds ports to `127.0.0.1` only. `backend` waits for its healthcheck before `frontend` starts. Both services use `app-network`; SQLite persists in named volume `ayonikah-planner-data`. `docker compose down` keeps this volume. Do not use `docker compose down -v` unless deleting local database data is intended.

Development images use production commands: FastAPI runs Uvicorn and Next.js runs `next start` after `next build`. For live reload, use local commands below.

## Configuration

Compose reads optional `.env` in repository root; values below contain safe local defaults:

| Variable | Compose default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Browser API URL; compiled into frontend image, rebuild after changing |
| `DATABASE_PATH` | `/data/planner.sqlite3` | SQLite file inside backend data volume |
| `UPLOAD_DIR` | `/data/uploads` | Persistent uploaded images inside same volume |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated trusted browser origins |
| `MAX_UPLOAD_BYTES` | `5242880` | Maximum image upload size (5 MiB) |

`NEXT_PUBLIC_*` values are public browser bundle configuration, never secrets. `.env.example` shows the Compose/container paths; backend's local default remains `backend/planner.sqlite3`.

## Local development

Run commands from repository root. Use separate terminals.

```sh
# Backend (Python 3.10+)
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (Node.js; second terminal)
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`. SQLite database defaults to `backend/planner.sqlite3`; Docker sets `DATABASE_PATH=/data/planner.sqlite3` inside named volume. Frontend defaults to `http://localhost:8000`; override with `NEXT_PUBLIC_API_URL`.

## Verification

```sh
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
```

Docker checks, when Docker is available:

```sh
docker compose config
docker compose build
```

## Troubleshooting

- `docker: command not found`: install/start Docker Desktop, then rerun commands.
- Port `3000` or `8000` busy: stop process using port, or change host-side port mapping in `docker-compose.yml`.
- Frontend cannot reach API: verify `NEXT_PUBLIC_API_URL`, rebuild after changing it, and check `docker compose logs backend`.
- Database reset needed: stop services, then explicitly run `docker volume rm ayonikah-planner-data`; this permanently deletes local planner data.
- Healthcheck failed: inspect `docker compose ps` and `docker compose logs backend frontend`.

## CORS

Development API permits `http://localhost:3000` and `http://127.0.0.1:3000`. Add exact trusted origins in `backend/main.py` before using a different frontend origin. Do not use wildcard origins with credentials.

## Secrets and data safety

Commit `.env.example`, never personal `.env` files. `.gitignore` excludes environment files, dependencies, build output, caches, virtualenvs, SQLite files, and local secrets. Compose does not remove volumes during normal stop/down.

## Production limitations

This is a single-user starter, not production-hardened: no authentication/authorization, multi-user isolation, CSRF policy, TLS termination, backups/restore, database concurrency tuning, image-content sniffing/re-encoding, or rate limiting. Uploaded image checks trust client-supplied MIME type and enforce size only; do not expose API publicly without adding appropriate controls. External image URLs are rendered directly by the browser. SQLite named volume is local persistence, not backup. Docker binds services to loopback by default.
