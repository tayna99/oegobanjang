"""인바운드 채널 webhook — Zalo OA(stage ④). MESSAGING_CHANNELS.md §3.

"Zalo OA webhook은 붙는 시점부터 같은 정규화 지점(Message{direction:'in'} 생성)에 합류한다.
인바운드 소스가 응답 링크든 webhook이든 그 다음 단계(N02 → M6 Interpretation)는 동일하다."
— 이 파일은 그 합류 지점 앞에서 Zalo 고유의 수신 형태(원시 페이로드)만 우리 정규화 함수
(`app/services/response_link.ingest_inbound_reply`) 입력으로 바꾼다.

한계(의도적으로 남긴 것): 실 Zalo OA webhook은 발신자를 Zalo 자체 `user_id`로 알려주는데,
이 스키마엔 근로자당 Zalo user_id를 저장하는 컬럼이 없다(전화번호와 동일한 이유로 PII 최소화
원칙상 이번 태스크 범위에서 새로 추가하지 않았다) — 그래서 이 MVP 웹훅은 `thread_id`를
페이로드에 직접 받는다(실 연동에서는 우리가 이전에 그 스레드로 보낸 메시지의 메타데이터에
추적 파라미터를 심어 되돌려받는 방식이 일반적이다). "Zalo user_id → thread_id 해석"은 그
매핑 컬럼이 생기는 시점의 후속 과제로 명시적으로 남긴다 — 지금 붙이는 것은 §3이 요구하는
"같은 정규화 지점 합류"이지, 그 앞단의 사용자 식별 문제가 아니다.
"""

from __future__ import annotations

import hmac

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.webhook_exceptions import WebhookNotConfiguredError, WebhookThreadNotFoundError, WebhookUnauthorizedError
from app.models.thread import Thread
from app.models.worker import Worker
from app.services.response_link import ingest_inbound_reply


def verify_zalo_webhook_secret(provided_secret: str | None) -> None:
    configured = get_settings().zalo_webhook_secret
    if not configured:
        # 자격 증명(공유 시크릿) 없음 — 채널 어댑터의 "credentials unset → 실제 처리 금지"
        # 원칙을 인바운드에도 동일하게 적용한다(위조 인바운드로 evidence를 오염시키지 않는다).
        raise WebhookNotConfiguredError()
    if not provided_secret or not hmac.compare_digest(provided_secret, configured):
        raise WebhookUnauthorizedError()


def ingest_zalo_webhook(db: Session, *, thread_id: str, text: str) -> None:
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise WebhookThreadNotFoundError(thread_id)
    worker = db.get(Worker, thread.worker_id) if thread.worker_id else None
    lang = worker.preferred_language if worker else None

    ingest_inbound_reply(
        db,
        company_id=thread.company_id,
        thread_id=thread_id,
        lang=lang,
        body_original=text,
        confidence="low",  # webhook은 항상 자유 입력(구조화 버튼 선택이 없다)
        summary_ko="근로자 응답 수신 · 자유 입력(원문은 스레드에서 확인)",
        source="Zalo webhook",
    )
