# Fitness Tracker

Self-hosted fitness tracker for body measurements, workout programs, gym-mode
set logging, nutrition, Friday check-ins, and deterministic weekly reports.

There is **no AI**. Program generation, progression suggestions, analytics, and
reports use ordinary application logic.

## Screenshots

Add screenshots here after you run the app.

## Architecture

- React + Vite frontend (PWA)
- FastAPI backend
- SQLite in WAL mode
- Single Docker image that serves the API and the built frontend

See `docs/ARCHITECTURE.md` and `docs/DATA_MODEL.md`.

## Technology stack

Frontend: React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS, Recharts, Lucide, PWA.

Backend: Python 3.12, FastAPI, SQLAlchemy 2, Pydantic, Alembic.

Database: SQLite (WAL). Models are conventional SQLAlchemy so PostgreSQL is a later option.

## Local development

Prerequisites: Python 3.12+, Node 22+.

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:FITNESS_TESTING="0"
uvicorn app.main:app --reload --port 8000

# Frontend (another terminal)
cd frontend
nvm use 22.18.0
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/api` to port 8000).

Create an account on first launch. Onboarding collects height, weight, goal, and equipment.

## Production / Docker

```powershell
copy .env.example .env
# set SECRET_KEY in .env
docker compose up -d --build
```

Default URL: http://localhost:8080

## Raspberry Pi (ARM64)

The Dockerfiles use official `bookworm` images and are ARM64 compatible.

```bash
git clone <this-repo>
cd Fitness-Tracker
cp .env.example .env
# edit SECRET_KEY
docker compose up -d --build
```

Point your existing Cloudflare Tunnel at `http://localhost:8080`. Cloudflare is
not required on the LAN.

## Database

Default local file: `data/fitness.db`

Docker volume: `fitness-data` mounted at `/data/fitness.db`

Tables are created on startup. Alembic revision `001_initial` matches the models.

## Exercise seed

Vendored from [yuhonas/free-exercise-db](https://github.com/yuhonas/free-exercise-db)
(public domain). Loaded automatically if the exercise table is empty. Images are
imported into `data/exercise-images` (Docker: `/data/exercise-images`) and served
locally from `/media/exercises`. Pages do not fetch GitHub.

```
python backend/scripts/seed_exercises.py
python backend/scripts/import_exercise_images.py
```

## Demo data (optional)

Never inserted automatically.

```
python backend/scripts/seed_demo.py
```

Login: `demo@local` / `demodemo`

## Backups

Use the SQLite backup API (WAL-safe). Do not copy a live `.db` plus `-wal` by hand.

```
python backend/scripts/backup_db.py backup --db data/fitness.db
python backend/scripts/backup_db.py restore --db data/fitness.db --file data/backups/fitness-YYYYMMDD.db
```

## Environment variables

| Name | Purpose |
| --- | --- |
| `SECRET_KEY` | JWT signing key. Change in production. |
| `DATABASE_URL` | SQLAlchemy URL. Docker default `sqlite:////data/fitness.db` |
| `USDA_FDC_API_KEY` | Optional. Not required for MVP food logging. |
| `CORS_ORIGINS` | Comma-separated origins for local Vite. |
| `EXERCISE_IMAGES_DIR` | Persistent exercise image directory. Docker: `/data/exercise-images`. |

## Cloudflare Tunnel

If `cloudflared` is already running, add a public hostname whose service is
`http://localhost:8080` (or the Pi's LAN IP). Do not put tunnel credentials in
this repo. The app works on the LAN without Cloudflare.

## Testing

```
cd backend
.\.venv\Scripts\python.exe -m pytest
cd ../frontend
npm test
npm run typecheck
npm run lint
npm run build
```

## Estimated 1RM

Epley: `1RM = weight × (1 + reps / 30)`, only for sets of 12 reps or fewer.
