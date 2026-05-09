from langchain_core.tools import BaseTool
from app.agent_runtime.schemas.tool import ToolContractLevel
from .safe_read import (
    get_candidate_readiness,
    get_worker_profile,
    get_visa_status,
    get_document_status,
    search_policy_documents,
    get_document_requirements,
)
from .safe_calculate import (
    calculate_visa_d_day,
    calculate_missing_documents,
    calculate_contract_gap,
)
from .safe_draft import (
    generate_multilingual_message_draft,
    generate_expert_handoff_package_draft,
)
from .approval_required import (
    send_worker_message,
    send_expert_package,
    update_case_status_completed,
)

SAFE_READ_TOOLS: list[BaseTool] = [
    get_worker_profile,
    get_visa_status,
    get_document_status,
    get_candidate_readiness,
    search_policy_documents,
    get_document_requirements,
]

SAFE_CALCULATE_TOOLS: list[BaseTool] = [
    calculate_visa_d_day,
    calculate_missing_documents,
    calculate_contract_gap,
]

SAFE_DRAFT_TOOLS: list[BaseTool] = [
    generate_multilingual_message_draft,
    generate_expert_handoff_package_draft,
]

APPROVAL_REQUIRED_TOOLS: list[BaseTool] = [
    send_worker_message,
    send_expert_package,
    update_case_status_completed,
]

TOOL_REGISTRY: dict[str, tuple[BaseTool, ToolContractLevel]] = {
    **{t.name: (t, ToolContractLevel.SAFE_READ) for t in SAFE_READ_TOOLS},
    **{t.name: (t, ToolContractLevel.SAFE_CALCULATE) for t in SAFE_CALCULATE_TOOLS},
    **{t.name: (t, ToolContractLevel.SAFE_DRAFT) for t in SAFE_DRAFT_TOOLS},
    **{t.name: (t, ToolContractLevel.APPROVAL_REQUIRED) for t in APPROVAL_REQUIRED_TOOLS},
}


def get_tools_by_grade(grade: ToolContractLevel) -> list[BaseTool]:
    return [tool for tool, g in TOOL_REGISTRY.values() if g == grade]


def get_all_safe_tools() -> list[BaseTool]:
    return SAFE_READ_TOOLS + SAFE_CALCULATE_TOOLS + SAFE_DRAFT_TOOLS
