from fastapi import FastAPI

from app.api.v1.approvals import router as approvals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.briefings import router as briefings_router
from app.api.v1.citations import router as citations_router
from app.api.v1.runs import router as runs_router

app = FastAPI(
    title="외고반장 API",
    description="docs/DB_SCHEMA.md 정본 기반 백엔드 접속점. 화면 라우터는 화면이 백엔드에 "
    "붙는 순서대로 점진 추가된다 — 현재는 로그인(phone+OTP)·승인 요청 생성·승인 decide· "
    "근거 라이브러리 조회·오케스트레이션 런(SSE)·데일리 브리핑 생성 엔드포인트까지"
    "(plans/HANDOFF.md).",
)

app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(citations_router)
app.include_router(runs_router)
app.include_router(briefings_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
