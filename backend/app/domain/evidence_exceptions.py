"""판단 기록(evidence_events) 일반 기록 도메인 예외 — app/api/v1/evidence.py가 HTTP 상태로 변환한다."""


class EvidenceError(Exception):
    """모든 evidence 도메인 예외의 기반 클래스."""


class EvidenceInvalidTypeError(EvidenceError):
    """허용 목록 밖 타입, 또는 무인증 패키지 링크 전용 타입(services/evidence.py 참조)."""

    def __init__(self, type_: str) -> None:
        super().__init__(f"허용되지 않는 판단 기록 타입입니다: {type_}")
        self.type = type_


class EvidenceReasonContainsPiiError(EvidenceError):
    """summary에 등록번호·여권번호·전화번호로 보이는 패턴이 감지됨(rules/safety.md)."""

    def __init__(self) -> None:
        super().__init__("요약에 개인정보로 보이는 값이 포함되어 있어 저장할 수 없습니다")


class EvidenceCaseNotFoundError(EvidenceError):
    """case_id가 제공됐는데 이 회사 소속 케이스가 아님 — 남의 회사 케이스 참조 차단."""

    def __init__(self, case_id: str) -> None:
        super().__init__(f"케이스를 찾을 수 없습니다: {case_id}")
        self.case_id = case_id
