"""행정사 화이트라벨 v1 도메인 예외(R5.1) — app/api/v1/expert.py가 HTTP 상태로 변환한다.

spec §4.2: 세션 뷰(패키지 조회)의 scope 밖·미승인·사무소 불일치는 전부 동일한 404
("존재하지 않음")로 응답한다(존재 비노출 원칙, 7단계 스펙 §1 / v0 §5와 동일). 내부 API의
403 관행과 다르다 — spec §4.2 각주가 이 편차를 명시적으로 인정하고 보안 리뷰 후속으로
남긴다.
"""


class ExpertError(Exception):
    """모든 행정사 화이트라벨 도메인 예외의 기반 클래스."""


class ExpertGrantForbiddenError(ExpertError):
    """위탁 발급/승인은 owner/manager, 철회는 owner 전용(spec §7.2)."""

    def __init__(self, message: str = "이 작업을 수행할 권한이 없습니다") -> None:
        super().__init__(message)


class ExpertGrantNotFoundError(ExpertError):
    def __init__(self, grant_id: str) -> None:
        super().__init__(f"위탁을 찾을 수 없습니다: {grant_id}")
        self.grant_id = grant_id


class ExpertGrantInvalidTransitionError(ExpertError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ExpertGrantUnboundedError(ExpertError):
    """무기한 위탁 금지(결정 C) — until은 필수이고 from보다 뒤여야 한다."""

    def __init__(self) -> None:
        super().__init__("위탁 기간(until)은 필수이며 시작일보다 뒤여야 합니다 — 무기한 위탁은 허용되지 않습니다")


class ExpertOfficeMemberNotFoundError(ExpertError):
    def __init__(self) -> None:
        super().__init__("사무소 구성원을 찾을 수 없습니다")


class ExpertOfficeMemberForbiddenError(ExpertError):
    """사무소 로스터 관리는 그 사무소의 isOfficeAdmin만(spec §5.6)."""

    def __init__(self) -> None:
        super().__init__("사무소 관리자만 구성원을 관리할 수 있습니다")


class ExpertAuthError(ExpertError):
    """email+OTP 세션 로그인 예외 — spec §3의 email+비밀번호를 이 저장소의 email+OTP
    패턴으로 특수화한 것에 대응(docs/DB_SCHEMA.md §4.8-1 편차 노트 참고)."""


class ExpertOtpNotFoundError(ExpertAuthError):
    def __init__(self) -> None:
        super().__init__("발급된 인증번호가 없습니다. 다시 요청해주세요")


class ExpertOtpExpiredError(ExpertAuthError):
    def __init__(self) -> None:
        super().__init__("인증번호가 만료되었습니다. 다시 요청해주세요")


class ExpertOtpAttemptsExceededError(ExpertAuthError):
    def __init__(self) -> None:
        super().__init__("인증 시도 횟수를 초과했습니다. 다시 요청해주세요")


class ExpertOtpCodeMismatchError(ExpertAuthError):
    def __init__(self) -> None:
        super().__init__("인증번호가 일치하지 않습니다")


class ExpertMemberNotRegisteredError(ExpertAuthError):
    """이 이메일로 등록된 사무소 구성원이 없다 — 위탁 초대 없이 임의 이메일로 로그인 불가."""

    def __init__(self) -> None:
        super().__init__("등록되지 않은 이메일입니다")


class ExpertMemberSuspendedError(ExpertAuthError):
    def __init__(self) -> None:
        super().__init__("정지된 계정입니다")


class ExpertSessionInvalidError(ExpertAuthError):
    def __init__(self) -> None:
        super().__init__("인증이 필요합니다")


class ExpertPackageNotFoundError(ExpertError):
    """3중 체크(spec §4.2) 실패는 사유 불문 전부 이 404 하나로 통일한다(존재 비노출)."""

    def __init__(self) -> None:
        super().__init__("존재하지 않습니다")
