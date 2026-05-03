from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


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