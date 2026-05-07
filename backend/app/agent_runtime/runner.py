import uuid
from app.agent_runtime.schemas import ForeignHiringState
from app.agent_runtime.graph.workflow import get_compiled_app


async def run_workflow(
    user_message: str,
    user_id: str,
    company_id: str,
    worker_id: str = "",
    candidate_id: str = "",
    thread_id: str | None = None,
) -> ForeignHiringState:
    app = get_compiled_app()

    request_id = str(uuid.uuid4())
    if thread_id is None:
        thread_id = request_id

    initial_state = ForeignHiringState(
        request_id=request_id,
        user_id=user_id,
        company_id=company_id,
        worker_id=worker_id,
        candidate_id=candidate_id,
        user_message=user_message,
    )

    config = {"configurable": {"thread_id": thread_id}}
    result_dict = await app.ainvoke(initial_state.model_dump(), config=config)

    return ForeignHiringState.model_validate(result_dict)
