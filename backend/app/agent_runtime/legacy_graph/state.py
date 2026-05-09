from typing import Annotated
from langgraph.graph import add_messages
from app.agent_runtime.schemas import ForeignHiringState

# LangGraph는 TypedDict 기반 state를 사용하므로 ForeignHiringState의 dict 표현을 활용합니다.
# graph 내부에서는 ForeignHiringState.model_dump() / model_validate() 로 변환합니다.

GraphState = ForeignHiringState
