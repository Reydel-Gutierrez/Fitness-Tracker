from app.api.analytics import export_router, router as analytics_router
from app.api.auth import router as auth_router
from app.api.body import router as body_router
from app.api.checkins import reports_router, router as checkins_router
from app.api.exercises import router as exercises_router
from app.api.goals import router as goals_router
from app.api.nutrition import router as nutrition_router
from app.api.profile import router as profile_router
from app.api.programs import router as programs_router
from app.api.sessions import router as sessions_router
from app.api.workouts import router as workouts_router

__all__ = [
    "auth_router",
    "profile_router",
    "body_router",
    "goals_router",
    "exercises_router",
    "workouts_router",
    "programs_router",
    "sessions_router",
    "nutrition_router",
    "checkins_router",
    "reports_router",
    "analytics_router",
    "export_router",
]
