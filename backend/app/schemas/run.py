from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RunCreateRequest(BaseModel):
    # Checkpoint key는 client input이 아니라 backend가 run/case 속성으로 생성한다.
    # 올드 클라이언트의 thread_id를 묵살하지 않고 422로 반환해 우회 스코프를 막는다.
    model_config = ConfigDict(extra="forbid")

    company_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)
