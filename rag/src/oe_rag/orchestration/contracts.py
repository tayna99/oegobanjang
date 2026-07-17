"""오케스트레이션 공용 계약 — legacy agent_runtime/schemas/* 이식.

발표 아키텍처(수정본 p.16 Agent Pattern)의 어휘를 코드로 정본화한다:
- Intent 8종(미션 라우팅용 상위 분류, LLM 구조화 출력 대상)
- Tool Contract 5등급(SAFE_READ/SAFE_CALCULATE/SAFE_DRAFT/APPROVAL_REQUIRED/FORBIDDEN)
- Evidence 이벤트 타입 9종(발표 p.17의 6종을 포함하는 상위집합)
- 승인 필요 액션 레지스트리(발표 "승인 6종" 숫자 정합의 정본:
  APPROVAL_REQUIRED tool 3종 + 자동실행 차단 액션 4종)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Intent(str, Enum):
    """미션 라우팅용 상위 의도 — legacy schemas/intent.py 이식."""

    HIRING = "HIRING"
    VISA_CHECK = "VISA_CHECK"
    DOCUMENT_CHECK = "DOCUMENT_CHECK"
    CONTACT = "CONTACT"
    BRIEFING = "BRIEFING"
    UNSUPPORTED_VALUE_JUDGMENT = "UNSUPPORTED_VALUE_JUDGMENT"
    UNSUPPORTED_LEGAL_JUDGMENT = "UNSUPPORTED_LEGAL_JUDGMENT"
    UNSUPPORTED_AUTO_SUBMISSION = "UNSUPPORTED_AUTO_SUBMISSION"


class ToolContractLevel(str, Enum):
    """Tool Contract 5등급 — legacy schemas/tool.py 이식 (발표 SVG §4)."""

    SAFE_READ = "SAFE_READ"
    SAFE_CALCULATE = "SAFE_CALCULATE"
    SAFE_DRAFT = "SAFE_DRAFT"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    FORBIDDEN = "FORBIDDEN"


class ToolStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    FORBIDDEN = "FORBIDDEN"


class ContractCitation(BaseModel):
    """Tool 결과에 실리는 인용 — legacy schemas/tool.py의 Citation 이식.

    (oe_rag.citation의 dict 헬퍼·agent.factory.RagCitation과 별개의 tool 계약용 모델)
    """

    source_id: str
    title: str
    evidence_grade: str
    publisher: str | None = None
    url: str | None = None
    excerpt: str | None = None


class ToolResult(BaseModel):
    tool_name: str
    tool_grade: ToolContractLevel
    status: ToolStatus
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    citations: list[ContractCitation] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    approval_required: bool = False
    error: str | None = None


class EventType(str, Enum):
    """Evidence 이벤트 타입 — legacy schemas/evidence.py 이식.

    발표 p.17 Evidence Log 6종(INTENT_CLASSIFIED/RAG_RETRIEVED/TOOL_EXECUTED/
    RISK_FLAGGED/APPROVAL_REQUESTED/FINAL_RESPONSE_GENERATED)을 포함한다.
    """

    INTENT_CLASSIFIED = "intent_classified"
    PLAN_CREATED = "plan_created"
    TOOL_EXECUTED = "tool_executed"
    RAG_RETRIEVED = "rag_retrieved"
    RISK_FLAGGED = "risk_flagged"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_COMPLETED = "approval_completed"
    HANDOFF_PACKAGE_DRAFT_CREATED = "handoff_package_draft_created"
    FINAL_RESPONSE_GENERATED = "final_response_generated"


class EvidenceEvent(BaseModel):
    """그래프가 방출하는 증빙 이벤트 프레임 — 영속화(INSERT-only)는 backend 책임."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    request_id: str
    agent_name: str | None = None
    step_name: str | None = None
    summary: str
    citation_ids: list[str] = Field(default_factory=list)
    risk_level: str = "LOW"
    approval_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# --- 승인·차단 액션 레지스트리 (발표 "승인 필요 액션" 숫자 정합의 정본) ------------------

# 사람 승인(Approval PENDING) 없이는 실행되지 않는 tool — legacy tools/approval_required.py
# 3종. 호출되면 항상 NEEDS_APPROVAL을 반환하고 실제 실행하지 않는다.
APPROVAL_REQUIRED_TOOLS: tuple[str, ...] = (
    "send_worker_message",
    "send_expert_package",
    "update_case_status_completed",
)

# LLM/에이전트가 자동 실행을 시도하면 즉시 차단되는 외부 경계 액션 — legacy
# build_blocked_response의 blocked_actions 4종.
AUTO_ACTION_BLOCKLIST: tuple[str, ...] = (
    "auto_send_to_candidate",
    "auto_send_to_sending_agency",
    "auto_send_to_admin_scrivener",
    "auto_submit_to_government_portal",
)

# 발표 자료의 "승인 필요 액션": 위 두 묶음의 합집합이 정본이다 (3 tool + 4 차단 = 7 경계,
# 발표 슬라이드 표기 "6종"은 government_portal 제출을 FORBIDDEN으로 따로 세는 계산).
APPROVAL_REQUIRED_ACTIONS: tuple[str, ...] = APPROVAL_REQUIRED_TOOLS + AUTO_ACTION_BLOCKLIST

# 등록 자체가 금지된 tool (발표 SVG §4 FORBIDDEN 등급) — 코드 어디에도 이 이름의 tool을
# 만들지 않는다. 레지스트리는 감사·테스트용 선언이다.
FORBIDDEN_TOOL_NAMES: tuple[str, ...] = (
    "submit_government_portal",
    "predict_absconding",
    "score_candidate",
    "confirm_visa_eligibility",
    "provide_legal_advice",
)
