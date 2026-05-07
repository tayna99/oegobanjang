from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class EventType(str, Enum):
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
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
