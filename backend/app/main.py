from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.approvals import router as approvals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.config import get_settings

app = FastAPI(
    title="외고반장 API",
    description="docs/DB_SCHEMA.md 정본 기반 백엔드 접속점. 화면 라우터는 화면이 백엔드에 "
    "붙는 순서대로 점진 추가된다 — 현재는 로그인(phone+OTP)·승인 요청 생성/조회·승인 decide·"
    "케이스 목록 읽기까지(plans/HANDOFF.md).",
)

# 코드 리뷰 지적(PR #12): 프론트(src/lib/api.ts, 다른 origin)가 JSON 본문 + Bearer 토큰으로
# 호출하면 브라우저가 preflight(OPTIONS)를 먼저 보낸다 — CORSMiddleware 없이는 여기서
# 막힌다. 쿠키를 안 쓰므로 allow_credentials=False로 두고 origin 매칭만 정확히 한다
# (config.Settings.resolved_cors_allow_origin_regex — None이면 미들웨어 자체를 안 붙인다).
_cors_origin_regex = get_settings().resolved_cors_allow_origin_regex
if _cors_origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=_cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(cases_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
