from __future__ import annotations

import pytest

from app.agent_runtime.langchain_v1.middleware import build_blocked_response
from app.agent_runtime.langchain_v1.runtime import normalize_runtime_input, run_langchain_v1_agent
from app.agent_runtime.langchain_v1.schemas import WorkBridgeAgentResponse


def test_candidate_value_judgment_is_blocked_with_pending_approval() -> None:
    response = build_blocked_response(
        reason="forbidden candidate judgment",
        user_message="성실하고 오래 일할 후보 추천해줘",
    )

    assert response.detected_intents == ["UNSUPPORTED_VALUE_JUDGMENT"]
    assert response.approval.required is True
    assert response.approval.status == "PENDING"
    assert "auto_send_to_candidate" in response.approval.blocked_actions


class _ForbiddenAutoSubmitAgent:
    async def ainvoke(self, payload):
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="정부 포털 제출은 자동 실행하지 않습니다.",
                detected_intents=["UNSUPPORTED_AUTO_SUBMISSION"],
                approval={
                    "required": True,
                    "status": "PENDING",
                    "reason": "정부 제출은 담당자 검토 필요",
                    "blocked_actions": ["auto_submit_to_government_portal"],
                },
                blocked_reason="government submission is not automated",
            )
        }


@pytest.mark.asyncio
async def test_auto_submission_request_stays_pending_and_blocked() -> None:
    state = await run_langchain_v1_agent(
        normalize_runtime_input(
            user_message="정부 포털에 비자 신청을 자동 제출해줘",
            company_id="company-001",
        ),
        agent=_ForbiddenAutoSubmitAgent(),
    )

    response = state.structured_response
    assert response.approval.required is True
    assert response.approval.status == "PENDING"
    assert "auto_submit_to_government_portal" in response.approval.blocked_actions
    assert response.blocked_reason


def test_external_execution_keywords_remain_blocked_actions() -> None:
    response = build_blocked_response(
        reason="external delivery blocked",
        user_message="행정사에게 패키지 바로 전송해줘",
    )

    assert response.approval.required is True
    assert "auto_submit_to_government_portal" in response.approval.blocked_actions
    assert "auto_send_to_admin_scrivener" in response.approval.blocked_actions
