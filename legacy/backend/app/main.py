import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = Path(__file__).resolve().parents[2]
for path in (BACKEND_DIR, ROOT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from .api.v1.router import router as api_v1_router
from .config import get_settings


settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="외국인 고용 운영 OS - FastAPI Backend",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    if settings.daily_briefing_scheduler_enabled:
        from .db.session import SessionLocal
        from .services.daily_briefing_scheduler import DailyBriefingBackgroundScheduler

        scheduler = DailyBriefingBackgroundScheduler(
            SessionLocal,
            interval_seconds=settings.daily_briefing_scheduler_interval_seconds,
            company_ids=settings.daily_briefing_scheduler_company_id_list,
            timezone_name=settings.daily_briefing_scheduler_timezone,
        )
        app.state.daily_briefing_scheduler = scheduler

        @app.on_event("startup")
        def start_daily_briefing_scheduler() -> None:
            scheduler.start(
                run_immediately=settings.daily_briefing_scheduler_run_on_startup
            )

        @app.on_event("shutdown")
        def stop_daily_briefing_scheduler() -> None:
            scheduler.stop()

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "status": "ok",
        }

    @app.get(f"{settings.api_v1_prefix}/health")
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "env": settings.app_env,
        }

    return app


app = create_app()
