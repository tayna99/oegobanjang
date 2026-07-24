"""GET/POST /api/v1/response-link/{token} — 근로자 응답 링크. 무인증(R3 stage ②).

ExpertLinkPage/packages.py의 무인증-토큰 패턴과 동일: 로그인 없이 접근하는 화면이라 이
파일만 `get_current_membership`을 거치지 않는다. MESSAGING_CHANNELS.md §3.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.response_link_exceptions import (
    ResponseLinkAlreadySubmittedError,
    ResponseLinkError,
    ResponseLinkExpiredError,
    ResponseLinkInvalidChoiceError,
    ResponseLinkNoContentError,
)
from app.schemas.response_link import (
    ResponseLinkSubmitRequest,
    ResponseLinkSubmitResponse,
    ResponseLinkViewOut,
    ResponseLinkWorkerOut,
)
from app.services.response_link import RESPONSE_CHOICES, get_response_link, submit_response

router = APIRouter(prefix="/api/v1/response-link", tags=["response-link"])

_ERROR_STATUS: dict[type[ResponseLinkError], int] = {
    ResponseLinkExpiredError: status.HTTP_404_NOT_FOUND,
    ResponseLinkAlreadySubmittedError: status.HTTP_409_CONFLICT,
    ResponseLinkNoContentError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ResponseLinkInvalidChoiceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


@router.get("/{token}", response_model=ResponseLinkViewOut)
def view_response_link(token: str, db: Session = Depends(get_db)) -> ResponseLinkViewOut:
    try:
        view = get_response_link(db, token)
    except ResponseLinkError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    worker_out = (
        ResponseLinkWorkerOut(display_name=view.worker.display_name, nationality=view.worker.nationality)
        if view.worker is not None
        else None
    )
    return ResponseLinkViewOut(
        thread_id=view.thread_id, worker=worker_out, lang=view.lang, prompt=view.prompt, choices=RESPONSE_CHOICES
    )


@router.post("/{token}", response_model=ResponseLinkSubmitResponse, status_code=status.HTTP_201_CREATED)
def post_response_link(
    token: str, payload: ResponseLinkSubmitRequest, db: Session = Depends(get_db)
) -> ResponseLinkSubmitResponse:
    try:
        submit_response(db, token, choice=payload.choice, free_text=payload.free_text)
    except ResponseLinkError as exc:
        raise HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc)) from exc
    return ResponseLinkSubmitResponse()
