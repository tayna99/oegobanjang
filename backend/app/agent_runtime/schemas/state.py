from typing import Any
from pydantic import BaseModel, Field
import uuid

from .intent import Intent
from .tool import ToolResult, Citation
from .evidence import EvidenceEvent


class ApprovalStatus(BaseModel):
    required: bool = False
    status: str = "NOT_REQUIRED"
    reason: str = ""


class ExecutionPlan(BaseModel):
    steps: list[str] = Field(default_factory=list)
    required_agents: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    blocked: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)


class ForeignHiringState(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    company_id: str = ""
    user_message: str = ""

    detected_intents: list[Intent] = Field(default_factory=list)
    plan: ExecutionPlan = Field(default_factory=ExecutionPlan)

    company_context: dict[str, Any] = Field(default_factory=dict)
    worker_context: dict[str, Any] = Field(default_factory=dict)
    candidate_context: dict[str, Any] = Field(default_factory=dict)

    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    rag_contexts: list[dict[str, Any]] = Field(default_factory=list)
    aggregated_output: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)

    approval: ApprovalStatus = Field(default_factory=ApprovalStatus)

    evidence_events: list[EvidenceEvent] = Field(default_factory=list)
    final_response: str = ""
