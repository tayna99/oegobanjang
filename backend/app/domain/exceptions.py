"""승인 결정 도메인 예외 — app/api/v1/approvals.py가 HTTP 상태 코드로 변환한다.

docs/DB_SCHEMA.md §5.3 승인 게이트 불변식 8개에 대응.
"""


class ApprovalError(Exception):
    """모든 승인 도메인 예외의 기반 클래스."""


class ApprovalNotFoundError(ApprovalError):
    def __init__(self, approval_id: str) -> None:
        super().__init__(f"승인 요청을 찾을 수 없습니다: {approval_id}")
        self.approval_id = approval_id


class ApprovalAlreadyDecidedError(ApprovalError):
    """pending이 아닌 승인에 다른 idempotency_key로 재결정을 시도함 — 409(§5.3-2, GOTCHAS §2)."""

    def __init__(self, current_status: str) -> None:
        super().__init__(f"이미 처리된 요청입니다 (현재 상태: {current_status})")
        self.current_status = current_status


class ApprovalForbiddenError(ApprovalError):
    """권한 없음 — 결정자 role 미달, high risk 케이스에 handoff 외 액션 승인 시도 등(§5.3-6·7)."""


class ApprovalBlockedByEvidenceError(ApprovalError):
    """사용 가능 근거(grade != 'F') 0건 — citation-0 잠금(§5.3-3, GOTCHAS §3)."""

    def __init__(self) -> None:
        super().__init__("근거가 없어 승인할 수 없습니다")


class ApprovalChecklistIncompleteError(ApprovalError):
    """checklist가 있는데 4항목 전부 checked가 아님(§5.3-5, M2.6 §2c)."""

    def __init__(self) -> None:
        super().__init__("필수 체크리스트를 모두 확인해야 승인할 수 있습니다")


class ApprovalIdentityRequiredError(ApprovalError):
    """승인 본인확인 수단(pin/biometric)이 없음 — 세션만으로 승인 불가(§5.3-6, 7단계 §4)."""

    def __init__(self) -> None:
        super().__init__("승인 본인확인(PIN 또는 생체인증)이 필요합니다")


class ApprovalPinNotRegisteredError(ApprovalError):
    """identity_method='pin'인데 users.pin_hash 미등록 — 422. POST /auth/pin으로 먼저 등록(§13-12)."""

    def __init__(self) -> None:
        super().__init__("승인 PIN이 등록되지 않았습니다. 먼저 PIN을 등록해주세요")


class ApprovalIdentityVerificationFailedError(ApprovalError):
    """본인확인 실패(PIN 불일치) — 403(§13-12). 어떤 값이 틀렸는지는 노출하지 않는다."""

    def __init__(self) -> None:
        super().__init__("본인확인에 실패했습니다")


class ApprovalBiometricUnsupportedError(ApprovalError):
    """identity_method='biometric'은 승인 API가 아직 받지 않는다 — 422(§13-12, 코드 리뷰 P1-3).

    users.biometric_registered 등록 여부만으로는 실제 생체 서명을 검증할 수 없다 — 세션만
    있으면 누구나 'biometric'이라고 주장해 통과시킬 수 있어, 실서명(WebAuthn 등) 검증이
    붙기 전까지는 pin만 유효한 identity_method로 받는다."""

    def __init__(self) -> None:
        super().__init__("생체 인증은 아직 지원하지 않습니다. PIN으로 본인확인해주세요")


class ApprovalReasonRequiredError(ApprovalError):
    def __init__(self) -> None:
        super().__init__("반려 시 사유가 필요합니다")


class ApprovalReasonContainsPiiError(ApprovalError):
    """반려 사유에 등록번호·여권번호·전화번호로 보이는 패턴이 감지됨(rules/safety.md)."""

    def __init__(self) -> None:
        super().__init__("반려 사유에 개인정보로 보이는 값이 포함되어 있어 저장할 수 없습니다")


class ApprovalIdempotencyKeyReusedError(ApprovalError):
    """idempotency_key가 다른(관련 없는) 승인 요청에 이미 쓰였음 — 클라이언트 버그, 409."""

    def __init__(self) -> None:
        super().__init__("idempotency_key가 다른 승인 요청에 이미 사용되었습니다")


class ApprovalAlreadyPendingError(ApprovalError):
    """대상 액션에 이미 pending 승인이 있음 — ux_approvals_one_pending 위반(§4.3), 409."""

    def __init__(self, action_id: str) -> None:
        super().__init__(f"이미 대기 중인 승인 요청이 있습니다: {action_id}")
        self.action_id = action_id


class ApprovalActionNotRequestableError(ApprovalError):
    """대상 액션이 requires_approval=false이거나 state != 'ready' — 422."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class CaseTransitionError(ApprovalError):
    """docs/DB_SCHEMA.md §5.1 화이트리스트 밖의 전이 — 버그로 취급, 409."""

    def __init__(self, from_state: str, to_state: str) -> None:
        super().__init__(f"허용되지 않은 상태 전이: {from_state} → {to_state}")
        self.from_state = from_state
        self.to_state = to_state
