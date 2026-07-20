"""발송 대기열(outbox) 도메인 예외 — app/api/v1/outbox.py가 HTTP 상태 코드로 변환한다.

MESSAGING_CHANNELS.md §2(발신 파이프라인) 규칙 위반에 대응.
"""


class OutboxError(Exception):
    """모든 outbox 도메인 예외의 기반 클래스."""


class OutboxActionNotFoundError(OutboxError):
    def __init__(self, action_id: str) -> None:
        super().__init__(f"액션을 찾을 수 없습니다: {action_id}")
        self.action_id = action_id


class OutboxForbiddenError(OutboxError):
    """실행 확인은 manager만 가능하다(MESSAGING_CHANNELS.md §1 각주² — owner는 승인만, 실행 대리 아님)."""

    def __init__(self) -> None:
        super().__init__("발송 실행 확인은 담당자(manager) 권한으로만 가능합니다")


class OutboxActionTypeNotSupportedError(OutboxError):
    """action_type이 'send_message'가 아님 — 이 큐는 근로자 채널 메시지 발송 전용이다."""

    def __init__(self, action_type: str) -> None:
        super().__init__(f"발송 대기열은 send_message 액션만 처리합니다 (현재: {action_type})")
        self.action_type = action_type


class OutboxApprovalNotApprovedError(OutboxError):
    """해당 액션에 대해 승인 완료(status='approved')된 approval이 없음 — 실행 확인의 구조적 전제."""

    def __init__(self, action_id: str) -> None:
        super().__init__(f"승인이 완료된 요청이 없어 발송을 실행할 수 없습니다: {action_id}")
        self.action_id = action_id


class OutboxAlreadyQueuedError(OutboxError):
    """같은 case+event_type+threshold(dedupe_key)가 이미 존재함 — 이벤트 idempotency(§2)."""

    def __init__(self, dedupe_key: str) -> None:
        super().__init__(f"이미 발송이 실행되었습니다: {dedupe_key}")
        self.dedupe_key = dedupe_key


class OutboxWorkerMissingError(OutboxError):
    """케이스에 연결된 근로자가 없음(삭제됨) — 수신자를 특정할 수 없다."""

    def __init__(self) -> None:
        super().__init__("케이스에 연결된 근로자가 없어 발송할 수 없습니다")


class OutboxNoThreadError(OutboxError):
    """근로자의 컨택 스레드가 없거나 채널이 근로자 채널(sms/alimtalk/zalo)이 아님."""

    def __init__(self) -> None:
        super().__init__("근로자의 컨택 채널을 찾을 수 없어 발송할 수 없습니다")


class OutboxNoContentError(OutboxError):
    """승인된 메시지 초안(drafts/draft_variants)이 없음 — 보낼 본문이 없다."""

    def __init__(self) -> None:
        super().__init__("승인된 메시지 초안이 없어 발송할 수 없습니다")


class OutboxReminderCooldownError(OutboxError):
    """같은 케이스의 재촉성 알림(reminder)이 24시간 내에 이미 발송됨(§2 리마인드 쿨다운)."""

    def __init__(self) -> None:
        super().__init__("같은 케이스의 리마인드는 24시간 내 재발송할 수 없습니다")


class OutboxResendNotEligibleError(OutboxError):
    """48시간 미응답 재발송 전제(원 발송 후 48h 경과 + 그 사이 근로자 응답 없음)를 만족하지 않음."""

    def __init__(self) -> None:
        super().__init__("48시간 미응답 재발송 조건을 만족하지 않습니다")
