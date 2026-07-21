"""M3 — 다국어 컨택 미션 (발표 p.15의 "다국어컨택 에이전트").

서브에이전트 2종 (legacy multilingual_contact_agent + contact_subagents 이식):
1. 연락온보딩/서류요청 메시지 — 다국어 근거 검색(결정론) → 메시지 초안(LLM 1회 또는
   결정론 템플릿). **항상 approval_required=True** — 발송은 승인 후 사람 몫(legacy 계약).
2. 답변해석 — 근로자 답변을 요약해 상태 업데이트 "후보"만 만든다. 자동 DB 반영 금지
   (p.15 "답변 ≠ 완료"), 원문·PII는 결과와 이벤트 어디에도 싣지 않는다
   (legacy _UNSAFE_SUMMARY_KEYS 계약을 가드로 이식).
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from ..agent.factory import RagAnswer, RagCitation
from ..agent.tools import search_multilingual_contact_materials
from ..orchestration.contracts import EventType
from ..orchestration.evidence import make_event
from ..orchestration.guard import assert_output_safety, redact_pii

MISSION_NAME = "m3_contact"

# legacy contact_subagents._UNSAFE_SUMMARY_KEYS 계약 — 결과 payload에 금지되는 키.
UNSAFE_RESULT_KEYS = frozenset(
    {"worker_reply", "raw_reply", "translated_ko", "korean_text", "translated_text", "message_body_full"}
)

_INTENT_TO_RAG_INTENT = {
    "contact_onboarding": "counseling",
    "document_request_message": "notice",
    "worker_reply_interpretation": "counseling",
}

_DRAFT_SYSTEM_PROMPT = (
    "당신은 외국인 근로자 다국어 안내 메시지 초안 작성기입니다. 공손한 존댓말 한국어 요약과 "
    "요청 목적·기한·연락 채널을 포함한 초안을 만드세요. 협박·불이익 표현 금지. "
    "이 초안은 발송이 아니라 담당자 승인용입니다."
)


class ContactDraft(BaseModel):
    korean_summary: str = Field(description="담당자용 한국어 요약")
    message_draft: str = Field(description="근로자에게 보낼 메시지 초안(대상 언어)")
    language: str = Field(default="ko", description="초안 언어 코드")


def run_m3_contact_mission(
    *,
    request_id: str,
    user_message: str,
    context_snapshot: dict[str, Any] | None = None,
    route: dict[str, Any] | None = None,
    chat_model: BaseChatModel | None = None,
) -> dict[str, Any]:
    snapshot = context_snapshot or {}
    intent = (route or {}).get("intent", "contact_onboarding")
    events: list[dict[str, Any]] = []

    # --- 다국어 근거 검색 (결정론) -------------------------------------------------------
    rag_intent = _INTENT_TO_RAG_INTENT.get(intent, "")
    retrieval = search_multilingual_contact_materials.invoke(
        {"query": user_message, "intent": rag_intent}
    )
    records = retrieval.get("records", [])
    citations = [
        RagCitation(
            source_id=str(r.get("source_id", "")),
            title=str(r.get("title", "")),
            evidence_grade=str(r.get("evidence_grade", "")),
        )
        for r in records
        if str(r.get("source_id", "")).strip()
        and str(r.get("evidence_grade", "")).upper() in {"A", "B", "E"}
    ]
    events.append(
        make_event(
            event_type=EventType.RAG_RETRIEVED,
            request_id=request_id,
            step_name="m3_contact.retrieve",
            agent_name=MISSION_NAME,
            summary=f"다국어 안내 근거 검색 {retrieval.get('retrieved_count', 0)}건",
            citation_ids=[c.source_id for c in citations][:10],
            risk_level="MEDIUM" if retrieval.get("missing_evidence") else "LOW",
        )
    )

    if intent == "worker_reply_interpretation":
        result = _interpret_reply(request_id, user_message, chat_model, events)
    else:
        result = _draft_message(request_id, user_message, snapshot, chat_model, events)

    final_response = result["final_response"]
    assert_output_safety(final_response)
    _assert_no_unsafe_keys(result)

    answer = RagAnswer(
        final_response=final_response,
        citations=citations,
        missing_evidence=bool(retrieval.get("missing_evidence")),
        risk_flags=result.get("risk_flags", []),
    )
    return {
        "mission": MISSION_NAME,
        "status": "SUCCESS",
        "artifact": result.get("artifact"),
        "structured_response": answer.model_dump(),
        "citation_catalog": [citation.model_dump() for citation in citations],
        "approval_required": True,  # 컨택 산출물은 항상 담당자 승인 필요 (legacy 계약)
        "risk_flags": result.get("risk_flags", []),
        "evidence_events": events,
    }


def _draft_message(
    request_id: str,
    user_message: str,
    snapshot: dict[str, Any],
    chat_model: BaseChatModel | None,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    language = _preferred_language(snapshot)
    if chat_model is not None:
        structured = chat_model.with_structured_output(ContactDraft)
        draft = structured.invoke(
            [
                {"role": "system", "content": _DRAFT_SYSTEM_PROMPT},
                {"role": "user", "content": f"요청: {user_message}\n대상 언어: {language}"},
            ]
        )
        if isinstance(draft, ContactDraft):
            korean_summary, message_draft, language = (
                draft.korean_summary,
                draft.message_draft,
                draft.language,
            )
        else:  # pragma: no cover - 방어
            korean_summary, message_draft = _template_draft(user_message)
    else:
        korean_summary, message_draft = _template_draft(user_message)

    events.append(
        make_event(
            event_type=EventType.HANDOFF_PACKAGE_DRAFT_CREATED,
            request_id=request_id,
            step_name="m3_contact.draft",
            agent_name=MISSION_NAME,
            summary=f"다국어 메시지 초안 생성({language}) — 발송 아님, 승인 대기",
            risk_level="LOW",
            metadata={"approval_required": True, "language": language},
        )
    )
    return {
        "final_response": (
            f"{korean_summary}\n\n[메시지 초안 · {language}]\n{message_draft}\n\n"
            "이 초안은 발송되지 않았습니다 — 담당자 승인 후 발송됩니다."
        ),
        "artifact": {
            "kind": "contact_message_draft",
            "language": language,
            "korean_summary": korean_summary,
            "message_draft": message_draft,
            "approval_required": True,
        },
        "risk_flags": [],
    }


def _interpret_reply(
    request_id: str,
    user_message: str,
    chat_model: BaseChatModel | None,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    masked = redact_pii(user_message)
    if chat_model is not None:
        summary_text = str(
            chat_model.invoke(
                [
                    {"role": "system", "content": "근로자 답변을 2문장 한국어로 요약하세요. 개인정보는 제외."},
                    {"role": "user", "content": masked},
                ]
            ).content
        )[:300]
    else:
        summary_text = "근로자 답변 요약은 담당자 검토가 필요합니다(오프라인 모드 — 자동 해석 생략)."

    candidates = [{"status": "reply_received", "confidence": "candidate", "auto_apply": False}]
    events.append(
        make_event(
            event_type=EventType.TOOL_EXECUTED,
            request_id=request_id,
            step_name="m3_contact.interpret",
            agent_name=MISSION_NAME,
            summary="근로자 답변 해석 — 상태 업데이트 후보 생성(자동 반영 금지)",
            risk_level="LOW",
            metadata={"candidate_count": len(candidates)},
        )
    )
    return {
        "final_response": (
            f"근로자 답변 요약: {redact_pii(summary_text)}\n"
            "상태 업데이트는 후보로만 생성했습니다 — 담당자 확인 후 반영됩니다."
        ),
        "artifact": {
            "kind": "worker_reply_interpretation",
            "summary": redact_pii(summary_text),
            "status_update_candidates": candidates,
            "manager_review_required": True,
        },
        "risk_flags": [],
    }


def _template_draft(user_message: str) -> tuple[str, str]:
    korean_summary = f"요청 요약: {redact_pii(user_message)[:80]} — 아래 초안을 검토하세요."
    message_draft = (
        "안녕하세요. 회사에서 안내드립니다. 필요한 서류와 일정은 아래와 같습니다. "
        "확인 후 회신 부탁드립니다. 문의는 담당자에게 연락주세요."
    )
    return korean_summary, message_draft


def _preferred_language(snapshot: dict[str, Any]) -> str:
    workers = snapshot.get("workers", [])
    for worker in workers:
        lang = worker.get("preferred_language")
        if lang:
            return str(lang)
    return "ko"


def _assert_no_unsafe_keys(result: dict[str, Any]) -> None:
    artifact = result.get("artifact") or {}
    leaked = UNSAFE_RESULT_KEYS & set(artifact)
    if leaked:
        raise ValueError(f"unsafe keys in contact artifact: {sorted(leaked)}")
