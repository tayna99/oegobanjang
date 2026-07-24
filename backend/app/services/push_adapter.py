"""푸시 발송 어댑터 — 자격증명 게이트 스텁. R5.4.

이 개발 환경·CI·리뷰어 PC에는 실 FCM/APNs 자격증명이 없다 — `app/api/v1/auth.py`의
`debug_code=code if get_settings().is_local else None` 게이트와 동일한 패턴으로, 실제 외부
발송 경로는 `PUSH_PROVIDER_CREDENTIALS` 환경변수가 설정된 경우에만 "열리는 것을 시도"한다.
이 저장소·CI·리뷰어 환경 어디에도 그 값이 없으므로 이 어댑터는 지금 항상 로그 전용
no-op으로 동작한다 — placeholder 자격증명으로 실 외부 호출을 시도하는 일은 없다(절대 금지
원칙, mission 지시 그대로).

docs/DB_SCHEMA.md §13-7 계약: `notifications`는 발신 "의도" 큐일 뿐이고 sent/delivered/failed
상태·timestamp는 DB가 구조적으로 차단한다(db/validate.py "notification sent status is
blocked"/"no delivery timestamp columns"). 그래서 이 어댑터는 발송 성공/실패를 notifications
행에 절대 기록하지 않는다 — 그 자체가 스키마 계약 위반이다. 호출은 순수 부가 효과(로그 또는
실제 발송)일 뿐, notifications.status는 이 함수 호출 여부와 무관하게 항상 'queued'로 남는다.

실 FCM/APNs SDK 연동은 이 함수 안의 분기를 채우는 후속 작업이다(sibling 메시징 트랙
docs/MESSAGING_CHANNELS.md의 SmsAdapter/AlimtalkAdapter와 동일한 성격) — 이번 R5.4는
"자격증명이 있으면 어디로 확장할지"를 보여주는 인터페이스 + 게이트만 제공한다.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.models.notification import Notification

logger = logging.getLogger("app.push")


def send_push(notification: Notification) -> None:
    """알림 1건에 대해 푸시 발송을 "시도"한다 — 자격증명 미설정 시 로그만 남기는 no-op.

    notifications 테이블에는 아무 것도 쓰지 않는다(§13-7 계약, 위 docstring 참조). 예외를
    던지지 않는다 — 호출부(services/notifications.py)가 알림 큐 적재 트랜잭션 한가운데서
    이 함수를 부르므로, 발송 어댑터의 실패가 알림 생성 자체를 롤백시켜서는 안 된다.
    """
    settings = get_settings()
    if not settings.push_provider_credentials:
        logger.info(
            "[push:stub] no-op — company=%s recipient=%s type=%s priority=%s "
            "(PUSH_PROVIDER_CREDENTIALS 미설정, 이 환경의 기본 상태)",
            notification.company_id,
            notification.recipient_user_id,
            notification.type,
            notification.priority,
        )
        return
    # 자격증명이 실제로 설정된 배포 환경에서만 도달한다 — 이 저장소는 아직 실 FCM/APNs SDK
    # 연동을 구현하지 않았다(R5.4 스코프 밖, §13-7 "발신 확인 없음" 설계와 정합 — 실
    # delivery 상태를 저장할 컬럼 자체가 없다). 자격증명이 있어도 지금은 로그만 남기고
    # no-op한다 — 실 SDK 호출 연결은 후속 마일스톤의 몫이다(placeholder 키로 실 호출 금지).
    logger.info(
        "[push:credentialed-stub] SDK 미구현 — company=%s recipient=%s type=%s (후속 작업 대상)",
        notification.company_id,
        notification.recipient_user_id,
        notification.type,
    )
