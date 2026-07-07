from app.agent_runtime.schemas import ForeignHiringState
from app.agent_runtime.langchain_v1.runtime import (
    normalize_runtime_input,
    run_langchain_v1_agent,
    to_foreign_hiring_state,
)


async def run_workflow(
    user_message: str,
    user_id: str,
    company_id: str,
    worker_id: str = "",
    candidate_id: str = "",
    thread_id: str | None = None,
    input_payload: dict | None = None,
) -> ForeignHiringState:
    runtime_input = normalize_runtime_input(
        user_message=user_message,
        user_id=user_id,
        company_id=company_id,
        worker_id=worker_id,
        candidate_id=candidate_id,
        thread_id=thread_id,
        input_payload=input_payload or {},
    )
    runtime_state = await run_langchain_v1_agent(runtime_input)
    return to_foreign_hiring_state(runtime_state)
