"""직선 오케스트레이션 그래프 — 발표 수정본 p.16 Agent Pattern의 구현.

입력채널 → [input_guard] → [intent_router] → [planner] → [executor(미션 순차)]
→ [aggregator] → [approval_gate] → [evidence_finalize] → END
                └(금지어·forbidden intent)→ [blocked_response] ────────┘

원칙(코드로 강제):
- LLM 자유 tool loop 없음 — 순서는 이 그래프가 소유하고, LLM은 라우팅 향상(선택)과
  미션 내부 초안·합성 1회만 담당한다.
- severity·rule 판단은 backend가 주입한 context_snapshot의 rule_findings를 소비만 한다.
- 외부 발송류는 approval_gate에서 pending-first로만 표시된다(실행 없음).
- checkpointer 없음: pending-first라 그래프 재개가 필요 없다(HITL resume은 B7).
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from ..agent.factory import RagAnswer
from ..missions.m1_workforce import run_m1_workforce_mission
from ..missions.m2_visa import run_m2_visa_mission
from ..missions.m3_contact import run_m3_contact_mission
from ..missions.rag_answer import run_rag_answer_mission
from .contracts import AUTO_ACTION_BLOCKLIST, EventType
from .evidence import make_event
from .guard import find_forbidden_input_terms, redact_pii
from .router import route_message
from .state import OrchestrationState

MissionRunner = Callable[..., dict[str, Any]]

# 미션 레지스트리 — 발표 p.15의 3미션 전부 등록(M7-G5 완료).
# briefing/audit 등 미등록 미션은 rag_answer(M0)로 폴백하되 플래그를 남긴다(조용한 폴백 금지).
MISSION_REGISTRY: dict[str, MissionRunner] = {
    "rag_answer": run_rag_answer_mission,
    "m1_workforce": run_m1_workforce_mission,
    "m2_visa": run_m2_visa_mission,
    "m3_contact": run_m3_contact_mission,
}

_BLOCKED_FINAL_RESPONSE = (
    "요청을 자동 처리하지 않았습니다. 후보 평가, 국적 선호, 비자 확정 판단, "
    "외부 자동 발송·제출은 담당자 검토가 필요합니다."
)


def build_orchestration_graph(chat_model: BaseChatModel | None = None):
    """컴파일된 직선 그래프 반환. chat_model은 미션 내부 합성 1회에만 전달된다."""

    def input_guard(state: OrchestrationState) -> dict[str, Any]:
        raw = state.get("user_message", "")
        masked = redact_pii(raw)
        forbidden = find_forbidden_input_terms(masked)
        events = [
            make_event(
                event_type=EventType.INTENT_CLASSIFIED,
                request_id=state["request_id"],
                step_name="input_guard",
                summary="입력 가드 통과" if not forbidden else f"금지어 차단: {len(forbidden)}건",
                risk_level="HIGH" if forbidden else "LOW",
                metadata={"pii_masked": masked != raw, "forbidden_terms": forbidden[:5]},
            )
        ]
        if forbidden:
            return {
                "user_message": masked,
                "pii_masked": masked != raw,
                "blocked": True,
                "blocked_reason": f"forbidden input terms: {', '.join(forbidden[:3])}",
                "evidence_events": events,
            }
        return {
            "user_message": masked,
            "pii_masked": masked != raw,
            "blocked": False,
            "evidence_events": events,
        }

    def intent_router(state: OrchestrationState) -> dict[str, Any]:
        plan = route_message(state["user_message"])
        events = [
            make_event(
                event_type=EventType.INTENT_CLASSIFIED,
                request_id=state["request_id"],
                step_name="intent_router",
                summary=f"의도 분류: {plan.intent} → 미션 {plan.mission or '-'}",
                risk_level="HIGH" if plan.intent == "forbidden" else "LOW",
                metadata={"blocked_actions": plan.blocked_actions},
            )
        ]
        updates: dict[str, Any] = {"route": plan.model_dump(), "evidence_events": events}
        if not plan.should_run:
            updates["blocked"] = plan.intent == "forbidden"
            updates["blocked_reason"] = f"intent={plan.intent}"
        return updates

    def planner(state: OrchestrationState) -> dict[str, Any]:
        route = state.get("route", {})
        events = [
            make_event(
                event_type=EventType.PLAN_CREATED,
                request_id=state["request_id"],
                step_name="planner",
                summary=f"계획 수립: {len(route.get('plan_steps', []))}단계 (코드 dict — LLM 아님)",
                metadata={
                    "plan_steps": route.get("plan_steps", []),
                    "required_context": route.get("required_context", []),
                },
            )
        ]
        return {"evidence_events": events}

    def executor(state: OrchestrationState) -> dict[str, Any]:
        route = state.get("route", {})
        mission_name = route.get("mission") or "rag_answer"
        runner = MISSION_REGISTRY.get(mission_name)
        fallback_used = False
        if runner is None:
            runner = MISSION_REGISTRY["rag_answer"]
            fallback_used = True

        result = runner(
            request_id=state["request_id"],
            user_message=state["user_message"],
            context_snapshot=state.get("context_snapshot") or {},
            route=route,
            chat_model=chat_model,
        )
        if fallback_used:
            result = {
                **result,
                "risk_flags": [*result.get("risk_flags", []), "MISSION_NOT_IMPLEMENTED"],
                "requested_mission": mission_name,
            }

        mission_events = result.pop("evidence_events", [])
        return {"mission_results": [result], "evidence_events": mission_events}

    def aggregator(state: OrchestrationState) -> dict[str, Any]:
        results = state.get("mission_results", [])
        snapshot = state.get("context_snapshot") or {}
        rule_findings = snapshot.get("rule_findings", [])
        key_findings = [
            f"{f.get('display_label') or f.get('risk_type')}: {f.get('severity')}"
            + (f" (D-{f['d_day']})" if f.get("d_day") is not None else "")
            for f in rule_findings[:5]
        ]
        risk_flags = sorted({flag for r in results for flag in r.get("risk_flags", [])})
        approval_needed = any(r.get("approval_required") for r in results)

        structured = next(
            (r["structured_response"] for r in results if r.get("structured_response")),
            None,
        )
        citation_catalog = next(
            (r["citation_catalog"] for r in results if isinstance(r.get("citation_catalog"), list)),
            [],
        )
        if structured is None:
            structured = RagAnswer(
                final_response="처리할 미션 결과가 없습니다.",
                missing_evidence=True,
                risk_flags=["NO_MISSION_RESULT"],
            ).model_dump()

        aggregated = {
            "key_findings": key_findings,
            "risk_flags": risk_flags,
            "approval_needed": approval_needed,
            "mission_count": len(results),
        }
        return {
            "aggregated": aggregated,
            "structured_response": structured,
            "citation_catalog": citation_catalog,
        }

    def approval_gate(state: OrchestrationState) -> dict[str, Any]:
        route = state.get("route", {})
        aggregated = state.get("aggregated", {})
        blocked_actions = route.get("blocked_actions", [])
        needs_approval = bool(aggregated.get("approval_needed") or blocked_actions)

        approval = {
            "required": needs_approval,
            "status": "PENDING" if needs_approval else "NOT_REQUIRED",
            "blocked_actions": blocked_actions or list(AUTO_ACTION_BLOCKLIST),
            "reason": "외부 발송·제출·상태 완료는 담당자 승인 후 실행됩니다." if needs_approval else "",
        }
        events = []
        if needs_approval:
            events.append(
                make_event(
                    event_type=EventType.APPROVAL_REQUESTED,
                    request_id=state["request_id"],
                    step_name="approval_gate",
                    summary="승인 대기 생성 (pending-first) — 자동 실행 없음",
                    risk_level="MEDIUM",
                    metadata={"blocked_actions": blocked_actions},
                )
            )
        return {"approval": approval, "evidence_events": events}

    def blocked_response(state: OrchestrationState) -> dict[str, Any]:
        answer = RagAnswer(
            final_response=_BLOCKED_FINAL_RESPONSE,
            citations=[],
            missing_evidence=False,
            risk_flags=["ORCHESTRATION_BLOCKED"],
        )
        approval = {
            "required": True,
            "status": "PENDING",
            "blocked_actions": list(AUTO_ACTION_BLOCKLIST),
            "reason": state.get("blocked_reason", "요청이 안전 규칙으로 차단되었습니다."),
        }
        return {"structured_response": answer.model_dump(), "approval": approval}

    def evidence_finalize(state: OrchestrationState) -> dict[str, Any]:
        events = [
            make_event(
                event_type=EventType.FINAL_RESPONSE_GENERATED,
                request_id=state["request_id"],
                step_name="evidence_finalize",
                summary="최종 응답 생성 완료",
                metadata={
                    "blocked": bool(state.get("blocked")),
                    "approval_status": (state.get("approval") or {}).get("status"),
                    "event_count": len(state.get("evidence_events", [])) + 1,
                },
            )
        ]
        return {"evidence_events": events}

    graph = StateGraph(OrchestrationState)
    graph.add_node("input_guard", input_guard)
    graph.add_node("intent_router", intent_router)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("aggregator", aggregator)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("blocked_response", blocked_response)
    graph.add_node("evidence_finalize", evidence_finalize)

    graph.add_edge(START, "input_guard")
    graph.add_conditional_edges(
        "input_guard",
        lambda s: "blocked_response" if s.get("blocked") else "intent_router",
        {"blocked_response": "blocked_response", "intent_router": "intent_router"},
    )
    graph.add_conditional_edges(
        "intent_router",
        lambda s: "planner" if s.get("route", {}).get("should_run") else "blocked_response",
        {"planner": "planner", "blocked_response": "blocked_response"},
    )
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "aggregator")
    graph.add_edge("aggregator", "approval_gate")
    graph.add_edge("approval_gate", "evidence_finalize")
    graph.add_edge("blocked_response", "evidence_finalize")
    graph.add_edge("evidence_finalize", END)

    return graph.compile()


def new_request_id() -> str:
    return str(uuid.uuid4())
