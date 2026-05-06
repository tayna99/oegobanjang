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

### 현재 완료 상태

- 다국어 Contact Agent Runtime/API/natural language extractor 연결 완료
- API endpoint는 `POST /api/v1/agent/run`을 사용
- 다국어 RAG Tool, Chroma retriever, message template, worker reply summary 연결 완료
- 자연어 요청에서 `task_type`, `language_code`, `message_purpose`, 일정/장소 일부를 추출해 `input_payload`를 보강
- Runtime output을 `persist_result=true`일 때 SQLite 운영 DB에 선택 저장하는 흐름 연결 완료
- SQLite 운영 DB는 실행 위치와 관계없이 `backend/data/oegobanjang.sqlite3`를 사용
- 자연어 extractor는 `worker_name`을 추출할 수 있지만 DB 저장에는 `input_payload.worker_id`가 필요
- Runtime 테스트 기준 `uv run pytest backend/tests` 34개 통과

현재 메시지 초안, 승인 필요 여부, Evidence Log 후보, 상태 업데이트 후보는 Runtime response로 반환된다.
`persist_result=true`와 `worker_id`가 함께 전달되면 `contact_messages`, `approvals`, `evidence_logs`, `status_update_candidates`에 저장된다.

### 다음 작업

1. workers 테이블/조회 기능 설계
2. `worker_name` 기반 `worker_id` lookup 연결
3. 저장된 contact message / approval 조회 API 구현
4. 승인 후 발송/상태 반영 apply 흐름 설계
5. Frontend Dashboard 연결
