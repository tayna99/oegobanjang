"""POST /api/v1/runs/stream — 자연어 커맨드 런을 SSE로 실행 (B3').

인증된 사용자가 요청한 회사의 멤버인지 확인한 뒤에만 실행한다(citations API와
동일한 테넌트 인가 패턴). 진행 상황은 run_service.execute_command_run()이 만드는
프레임을 그대로 SSE로 중계한다 — 이벤트명은 프레임의 "type" 값을 그대로 쓴다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.membership import Membership
from app.schemas.run import RunCreateRequest
from app.services.run_service import execute_command_run

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _event_stream(db: Session, *, company_id: str, user_id: str, message: str) -> AsyncIterator[str]:
    async for frame in execute_command_run(db, company_id=company_id, user_id=user_id, message=message):
        event_type = frame.pop("type")
        yield _sse(event_type, frame)


@router.post("/stream")
def create_run_stream(
    request: RunCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    membership = db.execute(
        select(Membership).where(
            Membership.company_id == request.company_id,
            Membership.user_id == user_id,
            Membership.status == "active",
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "해당 사업장 접근 권한이 없습니다")

    return StreamingResponse(
        _event_stream(
            db,
            company_id=request.company_id,
            user_id=user_id,
            message=request.message,
        ),
        media_type="text/event-stream",
    )
