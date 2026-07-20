"""POST /api/v1/webhooks/zalo — Zalo OA 인바운드 webhook. 무인증이지만 공유 시크릿으로 보호한다.

MESSAGING_CHANNELS.md §5 stage ④. 자격 증명(`ZALO_WEBHOOK_SECRET`)이 없으면(이 dev 환경 기본값)
503으로 항상 거부한다 — 발신 어댑터의 credential-gating 원칙을 인바운드에도 동일하게 적용한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.webhook_exceptions import WebhookNotConfiguredError, WebhookThreadNotFoundError, WebhookUnauthorizedError
from app.schemas.webhook import ZaloWebhookPayload
from app.services.webhooks import ingest_zalo_webhook, verify_zalo_webhook_secret

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/zalo", status_code=status.HTTP_204_NO_CONTENT)
def zalo_webhook(
    payload: ZaloWebhookPayload,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    db: Session = Depends(get_db),
) -> None:
    try:
        verify_zalo_webhook_secret(x_webhook_secret)
    except WebhookNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except WebhookUnauthorizedError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    try:
        ingest_zalo_webhook(db, thread_id=payload.thread_id, text=payload.text)
    except WebhookThreadNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
