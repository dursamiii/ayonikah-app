# Ayonikah frontend

Next.js App Router planner UI. Start API separately, then run:

```sh
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to API origin; defaults to `http://localhost:8000`. API client expects `GET/POST /api/plans` and `PATCH/DELETE /api/plans/{id}` with fields `title`, `category`, `status` (`todo`, `in_progress`, `done`), `event_date`, `notes`, and `image_url`.

Checks: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.
