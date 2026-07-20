from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.approvals import router as approvals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.briefings import router as briefings_router
from app.api.v1.cases import router as cases_router
from app.api.v1.citations import router as citations_router
from app.api.v1.delegations import router as delegations_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.expert import router as expert_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.outbox import router as outbox_router
from app.api.v1.packages import router as packages_router
from app.api.v1.response_link import router as response_link_router
from app.api.v1.runs import router as runs_router
from app.api.v1.threads import router as threads_router
from app.api.v1.webhooks import router as webhooks_router
from app.config import get_settings

app = FastAPI(
    title="외고반장 API",
    description="docs/DB_SCHEMA.md 정본 기반 백엔드 접속점. 화면 라우터는 화면이 백엔드에 "
    "붙는 순서대로 점진 추가된다 — 현재는 로그인(phone+OTP)·승인 요청/결정(PIN·위임 검증)· "
    "근거 라이브러리 조회·오케스트레이션 런(SSE)·데일리 브리핑 생성/조회·케이스/스레드 읽기· "
    "판단 기록 기록/조회·행정사 패키지 링크·위임 조회(R2.4~R2.6)· 발송 대기열·응답 링크·"
    "Zalo 인바운드 webhook(R3 stage ②~④)·알림 센터 조회/읽음 처리(R5.4)까지(plans/HANDOFF.md).",
)

# R2.1 — 프론트가 실서버 모드(VITE_API_MODE=real)에서 브라우저 fetch로 이 API를 직접
# 호출한다(다른 origin) — CORS 없이는 로컬 Vite(5173)에서도 모든 요청이 막힌다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_credentials=False,  # Bearer 토큰만 쓴다 — 쿠키 기반 인증 아님(자격 증명 공유 불필요)
    # R5.1 — PATCH 추가(사무소 구성원 상태 변경, /api/v1/expert/office-members/{id}).
    # 이전까지는 GET/POST만 있었다(이 리포지토리 최초의 PATCH 엔드포인트).
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(citations_router)
app.include_router(runs_router)
app.include_router(cases_router)
app.include_router(briefings_router)
app.include_router(threads_router)
app.include_router(evidence_router)
app.include_router(packages_router)
app.include_router(delegations_router)
app.include_router(expert_router)
app.include_router(outbox_router)
app.include_router(response_link_router)
app.include_router(webhooks_router)
app.include_router(notifications_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
