# Architecture

Single-process web app.

```
Browser / PWA
    -> FastAPI (/api/* JSON, / static SPA)
        -> SQLAlchemy
            -> SQLite WAL file
```

Business logic lives in `backend/app/services`, `analytics`, `progression`,
and `program_generator`. API routers stay thin.

Frontend is feature-oriented under `frontend/src/features` and `pages`.

Gym Mode persists every completed set immediately via `PATCH /api/sessions/{id}/sets/{setId}`.
Active session state is stored on the server (`status=in_progress`), so a refresh
reloads the workout. Rest timers use `Date.now()` end timestamps in `localStorage`.

Units: stored metric (kg/cm) internally; displayed using the profile unit preference.
