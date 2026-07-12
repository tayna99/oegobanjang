from fastapi import FastAPI

app = FastAPI(
    title="외고반장 API",
    description="docs/DB_SCHEMA.md 정본 기반 백엔드 접속점 — 현재는 헬스체크만. "
    "화면 라우터는 각 마일스톤(P1 승인 API 등) 착수 시 추가된다.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
