import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    analytics_router,
    auth_router,
    body_router,
    checkins_router,
    exercises_router,
    export_router,
    goals_router,
    nutrition_router,
    profile_router,
    programs_router,
    reports_router,
    sessions_router,
    workouts_router,
)
from app.config import get_settings
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.services.exercise_images import ensure_local_images, get_images_dir
import app.models  # noqa: F401


def seed_if_needed() -> None:
    from app.services.exercise_seed import seed_exercises

    db = SessionLocal()
    try:
        candidates = [
            Path(__file__).resolve().parent.parent / "seed_data" / "exercises.json",
            Path("/app/seed_data/exercises.json"),
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path:
            import json

            items = json.loads(path.read_text(encoding="utf-8"))
            seed_exercises(db, items)
    finally:
        db.close()
    # Copy bundled images into the persistent data volume. Download only when
    # the local copy is missing. Pages never fetch GitHub/CDN URLs.
    ensure_local_images(allow_download=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("FITNESS_TESTING") != "1":
        Base.metadata.create_all(bind=engine)
        seed_if_needed()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(body_router)
app.include_router(goals_router)
app.include_router(exercises_router)
app.include_router(workouts_router)
app.include_router(programs_router)
app.include_router(sessions_router)
app.include_router(nutrition_router)
app.include_router(checkins_router)
app.include_router(reports_router)
app.include_router(analytics_router)
app.include_router(export_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


MEDIA = get_images_dir()
MEDIA.mkdir(parents=True, exist_ok=True)
app.mount("/media/exercises", StaticFiles(directory=MEDIA), name="exercise-images")

STATIC = Path(__file__).resolve().parent.parent / "static"
if STATIC.exists():
    assets = STATIC / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("media/"):
            raise HTTPException(status_code=404)
        candidate = STATIC / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC / "index.html")
