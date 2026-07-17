from __future__ import annotations

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    company_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None
