"""응답 링크(response link) 도메인 예외 — app/api/v1/response_link.py가 HTTP 상태로 변환한다.

MESSAGING_CHANNELS.md §3 수신 파이프라인.
"""


class ResponseLinkError(Exception):
    """모든 응답 링크 도메인 예외의 기반 클래스."""


class ResponseLinkExpiredError(ResponseLinkError):
    """토큰이 존재하지 않거나 만료됨 — 존재 비노출 원칙(packages.py 관례와 동일), 둘 다 같은 메시지."""

    def __init__(self) -> None:
        super().__init__("응답 링크를 찾을 수 없거나 만료되었습니다")


class ResponseLinkNoContentError(ResponseLinkError):
    """choice·free_text가 둘 다 비어 있음 — 응답 내용이 없다."""

    def __init__(self) -> None:
        super().__init__("응답 내용이 없습니다")


class ResponseLinkAlreadySubmittedError(ResponseLinkError):
    """A response token is single-use, so retries cannot duplicate inbound records."""

    def __init__(self) -> None:
        super().__init__("이 응답 링크로 이미 응답을 접수했습니다")


class ResponseLinkInvalidChoiceError(ResponseLinkError):
    """Reject a choice that was not supplied by the response-link page."""

    def __init__(self) -> None:
        super().__init__("알 수 없는 응답 선택지입니다")
