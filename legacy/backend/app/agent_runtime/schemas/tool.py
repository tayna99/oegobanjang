from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ToolContractLevel(str, Enum):
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


class Citation(BaseModel):
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
    citations: list[Citation] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    approval_required: bool = False
    error: str | None = None
