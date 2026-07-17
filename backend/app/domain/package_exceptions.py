"""행정사 패키지 링크 도메인 예외 — app/api/v1/packages.py가 HTTP 상태로 변환한다."""


class PackageError(Exception):
    """모든 패키지 링크 도메인 예외의 기반 클래스."""


class PackageForbiddenError(PackageError):
    """링크 발급/재발급은 manager/owner 전용(7단계 §4 "재발급은 manager")."""

    def __init__(self) -> None:
        super().__init__("링크 발급 권한이 없습니다")


class PackageCaseNotFoundError(PackageError):
    def __init__(self, case_id: str) -> None:
        super().__init__(f"케이스를 찾을 수 없습니다: {case_id}")
        self.case_id = case_id


class PackageLinkNotFoundError(PackageError):
    """링크 미발급·만료·대상 없음을 모두 같은 404로 취급한다(존재 비노출 원칙, 7단계 §1)."""

    def __init__(self) -> None:
        super().__init__("링크를 찾을 수 없습니다")
