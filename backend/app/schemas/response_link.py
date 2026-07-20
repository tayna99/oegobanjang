from __future__ import annotations

from pydantic import BaseModel


class ResponseLinkWorkerOut(BaseModel):
    display_name: str
    nationality: str


class ResponseLinkViewOut(BaseModel):
    """GET /api/v1/response-link/{token} — 무인증. 발신 메시지 본문(근로자 모국어)과 버튼
    선택지만 내려준다 — 케이스·회사 등 내부 식별자는 노출하지 않는다."""

    thread_id: str
    worker: ResponseLinkWorkerOut | None
    lang: str | None
    prompt: str
    choices: dict[str, str]


class ResponseLinkSubmitRequest(BaseModel):
    choice: str | None = None
    free_text: str | None = None


class ResponseLinkSubmitResponse(BaseModel):
    received: bool = True
