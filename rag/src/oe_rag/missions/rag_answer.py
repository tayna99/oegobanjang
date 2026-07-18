"""M0 — 일반 근거 질의 미션 (결정론 파이프라인).

발표 비용 원칙("근거가 필요한 질문에만 RAG, LLM 호출 최소화")의 구현:
검색은 기존 @tool을 LLM 없이 `.invoke()`로 결정론 호출하고, LLM은 최종 응답 합성
1회만 쓴다(`with_structured_output(RagAnswer)`). 모델이 없으면(오프라인 데모/CI)
검색 결과를 결정론적으로 RagAnswer로 조립한다 — B1 OfflineEchoChatModel과 같은 원칙.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from ..agent.factory import RagAnswer, RagCitation
from ..agent.tools import retrieve_workforce_materials
from ..orchestration.contracts import EventType
from ..orchestration.evidence import make_event

MISSION_NAME = "rag_answer"

_SYNTH_SYSTEM_PROMPT = (
    "당신은 외국인 고용 운영 OS '외고반장'의 근거 응답 합성기입니다. "
    "아래 검색 결과만 근거로 한국어 답변을 작성하세요. 검색 결과에 없는 내용을 지어내지 말고, "
    "citations에는 검색 결과의 source_id만 사용하세요. 비자 가부 판정·법률 자문·후보 평가는 금지입니다."
)


def run_rag_answer_mission(
    *,
    request_id: str,
    user_message: str,
    case_type: str = "new_hiring",
    chat_model: BaseChatModel | None = None,
    context_snapshot: dict[str, Any] | None = None,  # M0은 상태 불필요 — 러너 공통 계약
    route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """검색(결정론) → 합성(LLM 최대 1회 / 오프라인 결정론) → 미션 결과 dict."""
    retrieval = retrieve_workforce_materials.invoke(
        {"query": user_message, "case_type": case_type}
    )
    records = retrieval.get("records", [])
    missing = bool(retrieval.get("missing_evidence"))

    events = [
        make_event(
            event_type=EventType.RAG_RETRIEVED,
            request_id=request_id,
            step_name="rag_answer.retrieve",
            agent_name=MISSION_NAME,
            summary=f"근거 검색 {retrieval.get('retrieved_count', 0)}건",
            citation_ids=[str(r.get("source_id", "")) for r in records][:10],
            risk_level="MEDIUM" if missing else "LOW",
            metadata={"missing_evidence": missing},
        )
    ]

    answer = _synthesize(user_message, records, missing, chat_model)

    return {
        "mission": MISSION_NAME,
        "status": "SUCCESS",
        "structured_response": answer.model_dump(),
        "approval_required": False,
        "risk_flags": answer.risk_flags,
        "evidence_events": events,
    }


def _synthesize(
    user_message: str,
    records: list[dict[str, Any]],
    missing: bool,
    chat_model: BaseChatModel | None,
) -> RagAnswer:
    if missing or not records:
        return RagAnswer(
            final_response="관련 공식 근거를 찾지 못했습니다. 담당자·행정사에게 확인 후 재질문을 권장합니다.",
            citations=[],
            missing_evidence=True,
            risk_flags=["MISSING_EVIDENCE"],
        )

    citations = [
        RagCitation(
            source_id=str(r.get("source_id", "")),
            title=str(r.get("title", "")),
            evidence_grade=str(r.get("evidence_grade", "")),
        )
        for r in records
        if str(r.get("evidence_grade", "")) not in {"D", "F"}
    ]

    if chat_model is not None:
        structured = chat_model.with_structured_output(RagAnswer)
        context_lines = "\n\n".join(
            f"[{r.get('source_id')}] ({r.get('evidence_grade')}) {r.get('title')}\n{r.get('excerpt', '')}"
            for r in records[:5]
        )
        result = structured.invoke(
            [
                {"role": "system", "content": _SYNTH_SYSTEM_PROMPT},
                {"role": "user", "content": f"질문: {user_message}\n\n검색 결과:\n{context_lines}"},
            ]
        )
        if isinstance(result, RagAnswer):
            # LLM이 만든 citation은 검색 결과 source_id 집합으로 제한(지어내기 차단)
            allowed = {c.source_id for c in citations}
            result.citations = [c for c in result.citations if c.source_id in allowed] or citations[:3]
            return result

    top = citations[:3]
    return RagAnswer(
        final_response="다음 근거를 참고하세요: " + "; ".join(c.title for c in top),
        citations=top,
        missing_evidence=False,
        risk_flags=[],
    )
