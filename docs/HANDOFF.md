# Handoff

## 1. 목적

이 문서는 팀원 또는 AI Agent가 작업을 이어받을 때 필요한 정보를 정리한다.

---

## 2. 현재 구조

Agent 관련 코드는 아래 경로에서 관리한다.

```txt
backend/app/agent_runtime/
```

---

## 3. 담당자별 역할

| 담당자 | 역할 | 주요 파일 |
|---|---|---|
| 김현욱 | Visa Document Agent | visa_agent.py, visa_risk_tool.py, document_check_tool.py |
| 임태나 | Workforce Agent | hiring_agent.py, quota_tool.py, hiring_request_tool.py |
| 유현희 | Multilingual Contact Agent | contact_agent.py, translation_tool.py |

---

## 4. 데이터 수집 위치

```txt
data-pipeline/raw
- 원본 문서

data-pipeline/processed
- 전처리 결과

data-pipeline/seed
- CSV/JSONL 구조화 데이터
```

---

## 5. 작업 시작 전 확인 문서

```txt
AGENTS.md
README.md
docs/PROJECT_BRIEF.md
docs/AI_OS_DESIGN.md
docs/RAG_STRATEGY.md
docs/TOOL_CONTRACT.md
docs/SECURITY_GUARDRAILS.md
missions/active/*.md
```

---

## 6. 금지 사항

- 승인 필요한 작업을 자동 실행하지 않는다.
- 비자 가능 여부를 확정하지 않는다.
- 민감정보 원문을 Evidence Log에 남기지 않는다.
- 근로자 감시 기능을 만들지 않는다.

---

## 7. 다음 작업

1. Agent Runtime Skeleton 구현
2. RAG Indexing 기본 구조 구현
3. Visa Document Agent 구현
4. Workforce Agent 구현
5. Multilingual Contact Agent 구현
6. Evidence Log 저장 연결
7. Frontend Dashboard 연결