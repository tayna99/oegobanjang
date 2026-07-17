from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.approvals import router as approvals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.briefings import router as briefings_router
from app.api.v1.cases import router as cases_router
from app.api.v1.threads import router as threads_router
from app.config import get_settings

app = FastAPI(
    title="외고반장 API",
    description="docs/DB_SCHEMA.md 정본 기반 백엔드 접속점. 화면 라우터는 화면이 백엔드에 "
    "붙는 순서대로 점진 추가된다 — 현재는 로그인(phone+OTP)·승인 요청 생성·승인 decide·"
    "케이스/브리핑/스레드 읽기 엔드포인트까지(plans/HANDOFF.md).",
)

# R2.1 — 프론트가 실서버 모드(VITE_API_MODE=real)에서 브라우저 fetch로 이 API를 직접
# 호출한다(다른 origin) — CORS 없이는 로컬 Vite(5173)에서도 모든 요청이 막힌다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_credentials=False,  # Bearer 토큰만 쓴다 — 쿠키 기반 인증 아님(자격 증명 공유 불필요)
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(cases_router)
app.include_router(briefings_router)
app.include_router(threads_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
