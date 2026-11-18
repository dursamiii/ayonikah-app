# ayonikah-app

Wedding planner built with Next.js, FastAPI, and SQLite.

## Repository layout

- `backend/` — FastAPI service, SQLite persistence, API tests.
- `frontend/` — Next.js application.
- `docs/API_CONTRACT.md` — shared planner item JSON contract and endpoints.

## Local run

Run commands from repository root. Use separate terminals.

```sh
# Backend (Python 3.10+)
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (Node.js; in a second terminal)
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`. API docs: `http://127.0.0.1:8000/docs`. SQLite database is generated at `backend/planner.sqlite3`; keep local data out of Git. Frontend defaults to `http://localhost:8000`; override with `NEXT_PUBLIC_API_URL` when needed.

## Verification

```sh
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
```

## CORS

Development API permits `http://localhost:3000` and `http://127.0.0.1:3000`. Add exact trusted origins in `backend/main.py` before using a different frontend origin. Do not use wildcard origins with credentials.

## Approval boundaries

Local scaffold and reversible code edits are in scope. Do not publish to GitHub, deploy, expose services publicly, modify credentials/permissions, or delete user data without explicit approval. Keep secrets in ignored environment files; commit only safe `.env.example` templates.

## Checkpoint evidence format

Record each checkpoint in the project Kanban root card. Include: project/repository and phase; numbered acceptance criteria with pass/fail/pending plus evidence; completed task IDs and verifiable handoffs; active task IDs, assignees, dependencies, latest status; next ready task and reason; QA/review findings and fix IDs; exact commands and exit codes; failure ID, category, exact error, root cause, recovery strategy and retry counts; blocker/approval needed; timestamp and last verified state. Unknown evidence remains pending, never pass.
