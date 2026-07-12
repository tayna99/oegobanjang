from fastapi import FastAPI

from app.api.v1.approvals import router as approvals_router

app = FastAPI(
    title="외고반장 API",
    description="docs/DB_SCHEMA.md 정본 기반 백엔드 접속점. 화면 라우터는 화면이 백엔드에 "
    "붙는 순서대로 점진 추가된다 — 현재는 승인 decide 엔드포인트까지(plans/HANDOFF.md).",
)

app.include_router(approvals_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
