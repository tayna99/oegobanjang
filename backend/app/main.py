from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.approvals import router as approvals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.briefings import router as briefings_router
from app.api.v1.cases import router as cases_router
from app.api.v1.threads import router as threads_router

app = FastAPI(
    title="외고반장 API",
    description="docs/DB_SCHEMA.md 정본 기반 백엔드 접속점. 화면 라우터는 화면이 백엔드에 "
    "붙는 순서대로 점진 추가된다 — 현재는 로그인(phone+OTP)·승인 요청 생성·승인 decide·"
    "케이스/브리핑/스레드 읽기 엔드포인트까지(plans/HANDOFF.md).",
)

# R2.2(NEXT_ROADMAP) — 로컬 프론트(Vite :5173)가 이 API(기본 :8000)를 호출할 수 있게 한다.
# 이 배선은 로컬 개발 전용이다 — 배포 환경 오리진은 실제 배포 시점에 재검토한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(cases_router)
app.include_router(briefings_router)
app.include_router(threads_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
