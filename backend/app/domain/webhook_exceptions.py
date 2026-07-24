"""인바운드 webhook 도메인 예외 — app/api/v1/webhooks.py가 HTTP 상태로 변환한다."""


class WebhookError(Exception):
    """모든 webhook 도메인 예외의 기반 클래스."""


class WebhookNotConfiguredError(WebhookError):
    """자격 증명(공유 시크릿)이 설정되지 않음 — 발신 어댑터와 동일한 게이팅 원칙을 인바운드에도
    적용한다: 검증 수단이 없으면 아무 요청도 처리하지 않는다(위조 인바운드 차단)."""

    def __init__(self) -> None:
        super().__init__("webhook이 아직 구성되지 않았습니다")


class WebhookUnauthorizedError(WebhookError):
    def __init__(self) -> None:
        super().__init__("webhook 시크릿이 일치하지 않습니다")


class WebhookThreadNotFoundError(WebhookError):
    def __init__(self, thread_id: str) -> None:
        super().__init__(f"스레드를 찾을 수 없습니다: {thread_id}")
        self.thread_id = thread_id
