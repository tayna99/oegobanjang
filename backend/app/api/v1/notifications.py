"""알림 센터 조회/읽음 처리 — GET /api/v1/notifications, POST /api/v1/notifications/{id}/read. R5.4.

생성 엔드포인트는 여기 없다 — app/services/evidence.py와 동일 원칙: 알림도 "실제로 그
이벤트가 일어난 서버 트랜잭션 안에서만" 생성돼야 위조 알림(예: 실제로 없던 승인 요청 알림)을
막을 수 있다. 생성은 app/services/notifications.py를 이벤트 발생 지점
(services/approvals.py·briefing_service.py)이 직접 호출한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.session import get_db
from app.models.membership import Membership
from app.schemas.notification import NotificationOut
from app.services.notifications import list_notifications, mark_notification_read

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_my_notifications(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    """본인 수신함만(company_id+recipient_user_id 스코프), 최신순."""
    notifications = list_notifications(db, company_id=membership.company_id, recipient_user_id=membership.user_id)
    return [NotificationOut.model_validate(n) for n in notifications]


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> NotificationOut:
    notification = mark_notification_read(
        db,
        company_id=membership.company_id,
        recipient_user_id=membership.user_id,
        notification_id=notification_id,
    )
    if notification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "알림을 찾을 수 없습니다")
    return NotificationOut.model_validate(notification)
