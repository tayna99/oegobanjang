import csv
from pathlib import Path
from typing import Any, Protocol

from app.agent_runtime.schemas import ContextBlocker, ForeignHiringState


_SEED_DIR = (
    Path(__file__).resolve().parents[5] / "data-pipeline" / "seed"
)

_DROP_KEYS = {
    "worker_reply",
    "translated_ko",
    "ocr_text",
    "document_body",
    "message_body",
}

_MASK_BY_KEY = {
    "phone": "[전화번호]",
    "mobile": "[전화번호]",
    "passport_number": "[여권번호]",
    "alien_registration_number": "[외국인등록번호]",
    "registration_number": "[외국인등록번호]",
    "address": "[주소]",
}


class ContextRepository(Protocol):
    def get_company(self, company_id: str) -> dict[str, Any] | None:
        ...

    def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        ...

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        ...


class InMemoryContextRepository:
    def __init__(
        self,
        *,
        companies: dict[str, dict[str, Any]] | None = None,
        workers: dict[str, dict[str, Any]] | None = None,
        candidates: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.companies = companies or {}
        self.workers = workers or {}
        self.candidates = candidates or {}

    def get_company(self, company_id: str) -> dict[str, Any] | None:
        return self.companies.get(company_id)

    def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        return self.workers.get(worker_id)

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        return self.candidates.get(candidate_id)


class CsvSeedContextRepository:
    def __init__(self, seed_dir: Path | None = None) -> None:
        self.seed_dir = seed_dir or _SEED_DIR

    def get_company(self, company_id: str) -> dict[str, Any] | None:
        return _find_by_id(self.seed_dir / "companies.csv", company_id)

    def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        return _find_by_id(self.seed_dir / "workers.csv", worker_id)

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        return _find_by_id(self.seed_dir / "candidates.csv", candidate_id)


def state_loader_node(
    state: ForeignHiringState,
    *,
    repository: ContextRepository | None = None,
) -> ForeignHiringState:
    repo = repository or CsvSeedContextRepository()
    blockers: list[ContextBlocker] = []

    worker = _load_optional(
        lookup_id=state.worker_id,
        getter=repo.get_worker,
        missing_type="missing_worker",
        missing_message="근로자 정보를 찾을 수 없습니다.",
        blockers=blockers,
    )
    candidate = _load_optional(
        lookup_id=state.candidate_id,
        getter=repo.get_candidate,
        missing_type="missing_candidate",
        missing_message="후보자 정보를 찾을 수 없습니다.",
        blockers=blockers,
    )

    company_id = state.company_id
    if not company_id and worker:
        company_id = str(worker.get("company_id", ""))
    if not company_id and candidate:
        company_id = str(candidate.get("company_id", ""))

    company = _load_optional(
        lookup_id=company_id,
        getter=repo.get_company,
        missing_type="missing_company",
        missing_message="사업장 정보를 찾을 수 없습니다.",
        blockers=blockers,
    )

    if company_id and not state.company_id:
        state.company_id = company_id
    state.company_context = _sanitize_context(company or {})
    state.worker_context = _sanitize_context(worker or {})
    state.candidate_context = _sanitize_context(candidate or {})
    state.context_blockers = blockers
    state.context_loaded = len(blockers) == 0
    return state


def _load_optional(
    *,
    lookup_id: str,
    getter,
    missing_type: str,
    missing_message: str,
    blockers: list[ContextBlocker],
) -> dict[str, Any] | None:
    if not lookup_id:
        return None

    value = getter(lookup_id)
    if value is None:
        blockers.append(
            ContextBlocker(
                type=missing_type,
                message=missing_message,
                severity="MEDIUM",
                id=lookup_id,
            )
        )
    return value


def _find_by_id(path: Path, row_id: str) -> dict[str, str] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("id") == row_id:
                return dict(row)
    return None


def _sanitize_context(context: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in context.items():
        if key in _DROP_KEYS:
            continue
        sanitized[key] = _MASK_BY_KEY.get(key, value)
    return sanitized
