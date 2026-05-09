import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent_runtime.schemas import ForeignHiringState, Intent, EventType
from app.agent_runtime.legacy_graph.nodes.evidence_logger import make_event, log_event
from app.config import get_settings

_SUPPORTED_INTENTS = [i.value for i in Intent]

_SYSTEM_PROMPT = f"""당신은 외국인 고용 운영 시스템의 Intent 분류기입니다.
사용자 메시지를 분석하여 다음 중 해당하는 intent를 모두 골라 JSON 배열로 반환하세요.

지원 intent:
- HIRING: 채용, 고용허가, 사업장 등록 관련
- VISA_CHECK: 비자 상태, 체류기간 만료, 갱신 관련
- DOCUMENT_CHECK: 서류 현황, 누락 서류, 제출 현황 관련
- CONTACT: 근로자에게 메시지 발송, 다국어 소통 관련
- BRIEFING: 현황 요약, 보고 관련
- UNSUPPORTED_VALUE_JUDGMENT: 성실도, 이탈 예측, 후보자 평가 등 가치 판단
- UNSUPPORTED_LEGAL_JUDGMENT: 비자 가능 여부 확정, 법률/노무 자문
- UNSUPPORTED_AUTO_SUBMISSION: 정부 포털 자동 제출, 비자 신청 대행

응답 형식: {{"intents": ["INTENT1", "INTENT2"]}}
지원하지 않는 요청은 UNSUPPORTED_* 로 분류하세요."""


def intent_router_node(state: ForeignHiringState) -> ForeignHiringState:
    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=state.user_message),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        intents = [Intent(i) for i in parsed.get("intents", []) if i in _SUPPORTED_INTENTS]
    except Exception:
        intents = []

    state.detected_intents = intents

    event = make_event(
        event_type=EventType.INTENT_CLASSIFIED,
        request_id=state.request_id,
        summary=f"감지된 intent: {[i.value for i in intents]}",
        step_name="intent_router",
    )
    return log_event(state, event)
