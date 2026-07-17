"""오프라인 스모크·테스트용 fake chat model.

실제 OpenAI 호출 없이 create_agent의 tool-calling + structured-output(ToolStrategy)
흐름을 구동한다: 1턴째는 retrieve_workforce_materials tool 호출, 2턴째는 검색 결과를
바탕으로 RagAnswer 구조화 응답을 tool call로 반환한다.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class ScriptedToolCallingChatModel(BaseChatModel):
    """고정 각본(tool_calls 시퀀스)을 순서대로 재생하는 fake 모델.

    - bind_tools()는 바인딩된 도구 이름을 기록만 하고 self를 반환한다(각본은 고정).
    - 매 _generate 호출마다 다음 각본 스텝의 AIMessage를 반환한다.
    """

    steps: list[list[dict[str, Any]]]
    """각 턴에서 반환할 tool_calls 목록. 마지막 턴은 구조화 응답(tool_call 1개)이어야 한다."""
    final_content: str = ""
    turn: int = 0
    bound_tool_names: list[str] = []

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedToolCallingChatModel":
        names = []
        for t in tools:
            name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None)
            if name:
                names.append(name)
        self.bound_tool_names = names
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        step = self.steps[min(self.turn, len(self.steps) - 1)]
        self.turn += 1
        content = self.final_content if self.turn >= len(self.steps) else ""
        message = AIMessage(
            content=content,
            tool_calls=[
                {"name": call["name"], "args": call["args"], "id": f"call_{self.turn}_{i}"}
                for i, call in enumerate(step)
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-calling-fake-chat-model"


def latest_tool_result(messages: list[BaseMessage]) -> dict[str, Any] | None:
    """가장 최근 ToolMessage의 결과를 dict로 파싱한다.

    LangChain의 ToolNode는 @tool 반환값(dict)을 ToolMessage.content에 넣을 때
    JSON 문자열로 직렬화한다 — content가 이미 dict인 경우도 방어적으로 처리한다.
    """
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            content = message.content
            if isinstance(content, dict):
                return content
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
    return None


class OfflineEchoChatModel(BaseChatModel):
    """`rag chat --offline` 데모용 — 실제 LLM 없이 도구 결과를 기계적으로 구조화 응답으로 변환.

    1턴: retrieve_workforce_materials를 tool_args로 호출.
    2턴: 그 tool 결과(citations/missing_evidence/risk_flags)를 그대로 RagAnswer로 옮긴다.
    실제 자연어 생성이 아니라 파이프라인 배선(tool 호출 → 구조화 응답)이 동작함을 증명하는 용도다.
    """

    tool_args: dict[str, Any] = Field(default_factory=dict)
    turn: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> "OfflineEchoChatModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.turn += 1
        if self.turn == 1:
            message = AIMessage(
                content="",
                tool_calls=[
                    {"name": "retrieve_workforce_materials", "args": self.tool_args, "id": "call_1"}
                ],
            )
            return ChatResult(generations=[ChatGeneration(message=message)])

        tool_result = latest_tool_result(messages) or {}
        records = tool_result.get("records", [])
        missing_evidence = bool(tool_result.get("missing_evidence"))
        risk_flags = tool_result.get("risk_flags", [])
        citations = [
            {
                "source_id": record.get("source_id", ""),
                "title": record.get("title", ""),
                "evidence_grade": record.get("evidence_grade", ""),
            }
            for record in records
            if record.get("evidence_grade") not in {"D", "F"}
        ]
        final_response = (
            "관련 공식 근거를 찾지 못했습니다. 행정사 검토가 필요합니다."
            if missing_evidence
            else "다음 근거를 참고하세요: " + "; ".join(c["title"] for c in citations[:3])
        )
        message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "RagAnswer",
                    "args": {
                        "final_response": final_response,
                        "citations": citations,
                        "missing_evidence": missing_evidence,
                        "risk_flags": risk_flags,
                    },
                    "id": "call_2",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "offline-echo-fake-chat-model"
