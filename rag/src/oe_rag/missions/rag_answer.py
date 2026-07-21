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
    citation_catalog = _citation_catalog(records)

    return {
        "mission": MISSION_NAME,
        "status": "SUCCESS",
        "structured_response": answer.model_dump(),
        # backend가 LLM의 citation metadata를 신뢰하지 않고, 선택된 source_id를
        # deterministic retrieval 결과의 정본 메타데이터로 재주입할 수 있게 한다.
        "citation_catalog": [citation.model_dump() for citation in citation_catalog],
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

    citations = _citation_catalog(records)

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
            # LLM이 만든 title·grade는 신뢰하지 않는다. source_id만 선택에 사용하고,
            # deterministic retrieval candidate에서 정본 메타데이터를 재주입한다.
            by_source_id = {citation.source_id: citation for citation in citations}
            selected: list[RagCitation] = []
            seen_source_ids: set[str] = set()
            for citation in result.citations:
                source_id = citation.source_id
                if source_id in seen_source_ids or source_id not in by_source_id:
                    continue
                seen_source_ids.add(source_id)
                selected.append(by_source_id[source_id].model_copy(deep=True))
            result.citations = selected or [citation.model_copy(deep=True) for citation in citations[:3]]
            return result

    top = citations[:3]
    return RagAnswer(
        final_response="다음 근거를 참고하세요: " + "; ".join(c.title for c in top),
        citations=top,
        missing_evidence=False,
        risk_flags=[],
    )


def _citation_catalog(records: list[dict[str, Any]]) -> list[RagCitation]:
    """Retriever가 준 허용 후보만 정본 citation catalog으로 사용한다."""
    return [
        RagCitation(
            source_id=str(record.get("source_id", "")),
            title=str(record.get("title", "")),
            evidence_grade=str(record.get("evidence_grade", "")),
        )
        for record in records
        if str(record.get("source_id", "")).strip()
        and str(record.get("evidence_grade", "")).upper() in {"A", "B", "E"}
    ]
