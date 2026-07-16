"""인증 도메인 예외 — app/api/v1/auth.py·app/api/deps.py가 HTTP 상태 코드로 변환한다."""


class AuthError(Exception):
    """모든 인증 도메인 예외의 기반 클래스."""


class OtpNotFoundError(AuthError):
    def __init__(self) -> None:
        super().__init__("발급된 인증번호가 없습니다. 다시 요청해주세요")


class OtpExpiredError(AuthError):
    def __init__(self) -> None:
        super().__init__("인증번호가 만료되었습니다. 다시 요청해주세요")


class OtpAttemptsExceededError(AuthError):
    def __init__(self) -> None:
        super().__init__("인증 시도 횟수를 초과했습니다. 다시 요청해주세요")


class OtpCodeMismatchError(AuthError):
    def __init__(self) -> None:
        super().__init__("인증번호가 일치하지 않습니다")


class UserNotFoundError(AuthError):
    def __init__(self) -> None:
        super().__init__("등록되지 않은 휴대폰 번호입니다")


class SessionInvalidError(AuthError):
    def __init__(self) -> None:
        super().__init__("인증이 필요합니다")
