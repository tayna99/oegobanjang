from typing import Any
from pydantic import BaseModel, Field

from .tool import Citation


class AgentOutput(BaseModel):
    result: str
    citations: list[Citation] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    approval_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
