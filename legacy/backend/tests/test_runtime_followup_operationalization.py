from __future__ import annotations

import json
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base
from backend.app.models.approval import Approval
from backend.app.models.company import Company
from backend.app.models.document import DocumentRequirement, WorkerDocument
from backend.app.models.evidence import EvidenceLog
from backend.app.models.hiring import Candidate
from backend.app.models.runtime_state import RUNTIME_STATE_TARGET_TYPE
from backend.app.models.user import User
from backend.app.models.worker import Worker
from backend.app.services.approval_service import approve_approval_for_company
from backend.app.services.context_data_service import (
    calculate_candidate_readiness,
    calculate_missing_documents_for_worker,
    get_worker_profile_data,
)
from backend.app.services.runtime_state_persistence_service import (
    RUNTIME_STATE_APPROVAL_REASON,
    save_runtime_state_snapshot,
)

from app.agent_runtime.langchain_v1.schemas import (
    AgentRuntimeInput,
    ApprovalBlock,
    LangChainRuntimeState,
    WorkBridgeAgentResponse,
)


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return factory()


def _seed_context(db: Session) -> None:
    db.add(User(id="user-001", email="manager@example.com", display_name="담당자"))
    db.add(
        Company(
            id="company-001",
            name="샘플테크",
            business_number="123-45-67890",
            industry="자동차부품 제조",
            region="충북 음성",
            address="충북 음성군",
            current_foreign_workers=35,
            housing_available=True,
            shift_type="주야 2교대",
            requested_role="assembly",
        )
    )
    db.add(
        Worker(
            id="worker-001",
            company_id="company-001",
            name="Nguyen Van A",
            nationality="VN",
            preferred_language="vi",
            visa_type="E-9",
            visa_expires_at="2026-06-01",
            contract_starts_at="2024-06-01",
            contract_ends_at="2027-06-01",
            status="ACTIVE",
        )
    )
    db.add(
        WorkerDocument(
            id="doc-001",
            company_id="company-001",
            worker_id="worker-001",
            doc_type="employment_contract",
            status="SUBMITTED",
        )
    )
    db.add(
        DocumentRequirement(
            id="req-001",
            case_type="stay_extension",
            visa_type="E-9",
            required_doc="employment_contract",
            required=True,
            source_id="internal-test",
        )
    )
    db.add(
        DocumentRequirement(
            id="req-002",
            case_type="stay_extension",
            visa_type="E-9",
            required_doc="passport_copy",
            required=True,
            source_id="internal-test",
        )
    )
    db.add(
        Candidate(
            id="candidate-001",
            company_id="company-001",
            nationality="VN",
            desired_role="assembly",
            available_from="2026-07-01",
            language="vi",
            passport=True,
            photo=False,
            health_check=False,
            understood_housing=True,
            understood_shift=False,
        )
    )
    db.commit()


def test_runtime_state_snapshot_has_alembic_migration_and_env_import() -> None:
    root = Path(__file__).resolve().parents[2]
    migration_files = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "backend/migrations/versions").glob("*.py")
    )
    env_source = (root / "backend/migrations/env.py").read_text(encoding="utf-8")

    assert "agent_runtime_state_snapshots" in migration_files
    assert "companies" in migration_files
    assert "worker_documents" in migration_files
    assert "AgentRuntimeStateSnapshot" in env_source
    assert "Company" in env_source
    assert "Candidate" in env_source


def test_alembic_upgrade_and_downgrade_smoke_for_runtime_context_tables(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "runtime-context.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    config = Config(str(ROOT_DIR / "backend/alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "backend/migrations"))

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    tables = set(sqlalchemy_inspect(engine).get_table_names())
    assert "agent_runtime_state_snapshots" in tables
    assert "companies" in tables
    assert "workers" in tables
    assert "candidates" in tables
    assert "worker_documents" in tables

    command.downgrade(config, "base")
    tables_after_downgrade = set(sqlalchemy_inspect(engine).get_table_names())
    assert "agent_runtime_state_snapshots" not in tables_after_downgrade
    assert "companies" not in tables_after_downgrade


def test_runtime_text_and_gitignore_are_operationalized() -> None:
    root = Path(__file__).resolve().parents[2]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")

    assert RUNTIME_STATE_APPROVAL_REASON == (
        "LangChain runtime 결과를 외부 전달하거나 후속 실행하기 전 담당자 승인이 필요합니다."
    )
    assert "frontend/node_modules/" in gitignore
    assert "frontend/.next/" in gitignore


def test_context_models_and_services_use_db_state_for_runtime_judgment() -> None:
    db = _db()
    _seed_context(db)

    worker = get_worker_profile_data("worker-001", db=db)
    missing = calculate_missing_documents_for_worker(
        "worker-001",
        "stay_extension",
        db=db,
    )
    readiness = calculate_candidate_readiness(company_id="company-001", db=db)

    assert worker is not None
    assert worker["visa_type"] == "E-9"
    assert missing["missing"] == [{"doc_type": "passport_copy", "notes": ""}]
    assert readiness[0]["candidate_id"] == "candidate-001"
    assert readiness[0]["readiness_status"] == "missing_required_info"
    assert "candidate_score" not in readiness[0]
    assert "nationality_preference" not in readiness[0]


def test_safe_tools_do_not_directly_read_seed_csv_files() -> None:
    root = Path(__file__).resolve().parents[2]
    for path in [
        root / "backend/app/agent_runtime/tools/safe_read.py",
        root / "backend/app/agent_runtime/tools/safe_calculate.py",
        root / "backend/app/agent_runtime/tools/safe_draft.py",
    ]:
        source = path.read_text(encoding="utf-8")
        assert "_read_csv" not in source
        assert "csv.DictReader" not in source
        assert "data-pipeline" not in source


def test_runtime_approval_records_limited_resume_without_external_execution() -> None:
    db = _db()
    approval = ApprovalBlock(
        required=True,
        status="PENDING",
        reason="외부 전달 전 담당자 승인이 필요합니다.",
        blocked_actions=["auto_send_to_sending_agency", "auto_submit_to_government_portal"],
    )
    state = LangChainRuntimeState(
        request_id="runtime-resume-001",
        input=AgentRuntimeInput(
            request_id="runtime-resume-001",
            user_message="E-9 신규 채용 준비",
            user_id="user-001",
            company_id="company-001",
        ),
        structured_response=WorkBridgeAgentResponse(
            final_response="신규 채용 준비 초안입니다.",
            detected_intents=["HIRING"],
            approval=approval,
        ),
        approval=approval,
        evidence_events=[],
    )
    snapshot = save_runtime_state_snapshot(db, state)
    approval_row = db.scalar(
        select(Approval).where(Approval.target_type == RUNTIME_STATE_TARGET_TYPE)
    )
    assert approval_row is not None
    db.commit()

    approve_approval_for_company(
        db,
        approval_id=approval_row.id,
        company_id="company-001",
        reviewed_by="manager-001",
        reason="검토 완료",
    )
    db.commit()

    saved_snapshot = db.get(type(snapshot), snapshot.request_id)
    approval_payload = json.loads(saved_snapshot.approval_json)
    structured_response = json.loads(saved_snapshot.structured_response_json)
    event_types = [
        row.event_type
        for row in db.scalars(
            select(EvidenceLog).where(EvidenceLog.approval_id == approval_row.id)
        ).all()
    ]

    assert approval_payload["resume"]["status"] == "completed_or_blocked"
    assert "approved_draft_finalization" in approval_payload["resume"]["completed_actions"]
    assert "external_delivery" in approval_payload["resume"]["blocked_actions"]
    assert structured_response["domain_payload"]["approval_resume"]["status"] == (
        "completed_or_blocked"
    )
    assert "approval_reviewed" in event_types
    assert "resume_requested" in event_types
    assert "resume_completed_or_blocked" in event_types
