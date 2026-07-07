# Agent Runtime

Agent Runtime은 외고반장의 AI 실행 모듈입니다.

---

## 전체 흐름

```txt
User Request
→ Intent Router
→ Planner
→ State Loader
→ Agent Execution
→ Approval Gate
→ Evidence Logger
→ Final Response
```

---

## 주요 폴더

```txt
graph/
- LangGraph 상태 머신

agents/
- 업무별 전문 Agent

rag/
- 공식 문서 검색, citation 생성

tools/
- Agent가 호출하는 기능 도구

schemas/
- Agent 내부 상태, Tool 결과, Evidence 이벤트 스키마
```

---

## 금지 원칙

Agent Runtime은 아래 작업을 직접 실행하지 않는다.

- 비자 가능 여부 확정
- 법률·노무 자문
- 정부 포털 제출
- 메시지 자동 발송
- 행정사 패키지 자동 전송
- 근로자 감시
- 이탈 예측
- 후보자 성실도 판단
- 국적별 추천

---

## 승인 필요 작업

아래 작업은 `approval_required=true`로 반환한다.

- 외국인 근로자에게 메시지 발송
- 행정사/노무사에게 패키지 전달
- 케이스 완료 처리
- 대외 문서 export
- 카톡/문자 푸시 발송

---

## Evidence Log

Agent Runtime은 주요 단계마다 Evidence Log 후보 이벤트를 생성한다.

필수 이벤트:

- intent_classified
- plan_created
- tool_executed
- rag_retrieved
- risk_flagged
- approval_requested
- final_response_generated