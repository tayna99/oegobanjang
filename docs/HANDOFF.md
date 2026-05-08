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
- Handoff Package는 전문가 전달용 초안만 생성하며, 실제 전달은 담당자 승인 이후 별도 단계에서만 가능
- Handoff Package 응답에는 `worker_id` 원문을 넣지 않고 `masked_worker_id`만 포함
- `worker_id`는 DB relation 또는 내부 state 연결용으로만 유지 가능
- Handoff Package에는 `approval_required=true`, `approval.status=PENDING`, `not_for_legal_judgment=true`를 유지
- Handoff Package와 Evidence Log에는 `worker_reply` 원문, `translated_ko` 전문, 근로자-facing message body 전문을 저장하지 않음
- Handoff draft 생성/저장/조회/승인/반려/API summary 흐름 완료
- 저장된 handoff draft는 `GET /api/v1/handoff-package-drafts/{draft_id}`로 safe detail 조회 가능
- 저장된 handoff draft는 draft id 기반 API와 공용 approval API 양쪽에서 승인/반려 가능
- company scope는 MVP 단계에서 `X-Company-Id` header 기준으로 검사
- 운영 전에는 인증 토큰 기반 company/role 검증으로 교체 필요
- 현재 service DB는 SQLite MVP 기준이며, 실제 구현 테이블은 `approvals`, `contact_messages`, `status_update_candidates`, `handoff_package_drafts`, `evidence_logs` 중심
- `companies`, `workers`, `candidates`, `worker_documents`, `users` 등 context tables는 아직 planned 상태이며 State Loader는 CSV seed repository를 사용

현재 메시지 초안, 승인 필요 여부, Evidence Log 후보, 상태 업데이트 후보는 Runtime response로 반환된다.
`persist_result=true`와 `worker_id`가 함께 전달되면 `contact_messages`, `approvals`, `evidence_logs`, `status_update_candidates`에 저장된다.

### Handoff Package 정책

Handoff Package는 `expert_handoff_draft` 타입의 초안이다.

LangGraph workflow에서는 아래 조건 중 하나일 때만 Handoff Package Draft를 자동 생성한다.

```txt
aggregated_output.risk_level == "HIGH"
또는 aggregated_output.approval_reasons에 "expert_handoff_package_draft" 포함
또는 aggregated_output.approval_reasons에 "expert_handoff_transfer" 포함
```

단순 메시지 초안, 단순 worker reply summary, 단순 정보 조회, `MEDIUM` 이하 일반 승인 케이스에서는 자동 생성하지 않는다.
자동 생성된 draft도 외부 전달물이 아니며, 전문가 전달 전 담당자 승인이 필요하다.

필수 상태:

```txt
package_type=expert_handoff_draft
approval_required=true
approval.status=PENDING
not_for_legal_judgment=true
raw_worker_reply_included=false
full_translation_included=false
message_body_included=false
```

응답 package의 `worker_summary`에는 아래 정보만 포함한다.

```txt
masked_worker_id
visa_type
stay_expires_at
contract_ends_at
```

기본 handoff draft에는 아래 원문을 포함하지 않는다.

```txt
worker_id 원문
worker_name 원문
nationality
worker_reply 원문
translated_ko 전문
근로자-facing message body 전문
여권번호
외국인등록번호
전화번호 전체
주소 전체
```

외부 전문가 전달은 `send_expert_package` 같은 approval-required tool이 담당하며, 해당 tool은 항상 `NEEDS_APPROVAL`을 반환해야 한다.

`handoff_package_draft`가 생성되면 `final_response`에는 초안 생성 및 승인 전 미전달 안내만 표시한다.
패키지 원문, `worker_id` 원문, `worker_reply` 원문, `translated_ko` 전문, 메시지 전문, 개인정보 원문은 `final_response`에 직접 포함하지 않는다.

LangGraph `user_message` 경로에서는 top-level `persist_result=true`일 때 생성된 handoff draft를 `handoff_package_drafts` 테이블에 저장한다.
Contact Runtime `user_request` 경로는 기존처럼 `input_payload.persist_result`를 사용하며, 현재 handoff draft를 만들지 않으므로 `handoff.available=false`를 반환한다.

저장된 handoff draft도 초안 상태다.

```txt
handoff_package_drafts.status=PENDING_APPROVAL
approval.target_type=handoff_package_draft
approval.status=PENDING
transferred_at=null
```

`worker_id`는 DB relation 필드로만 저장할 수 있고, `package_json`이나 API response draft body에는 저장하지 않는다.
`package_json`은 allowlist 기반으로 요약, 마스킹 ID, 서류 종류, 누락 여부, citation_id, risk_flags, approval 상태만 저장한다.

저장된 handoff draft는 아래 API로 조회할 수 있다.

```txt
GET /api/v1/handoff-package-drafts/{draft_id}
```

MVP/demo 단계에서는 `X-Company-Id` header를 접근 scope로 사용한다.
`X-Company-Id`가 없거나 `handoff_package_drafts.company_id`와 일치하지 않으면 `403 Forbidden`으로 차단한다.
운영 전에는 이 임시 header 정책을 인증 토큰 기반 `company_id`/role 검증으로 교체해야 한다.

조회 API는 safe detail view만 반환한다.
전체 `package_json` 원문, `worker_id` 원문, `worker_reply` 원문, `translated_ko` 전문, 근로자-facing message body 전문, 개인정보 원문은 반환하지 않는다.
`case_summary`와 `document_summary`는 저장 시 allowlist sanitize된 값에서만 가져오며, 조회 직전 금지 marker와 개인정보 패턴을 재검사한다.
조회 API는 read-only이며 전문가 전달, 외부 export, 메시지 발송, 정부 제출, 상태 확정을 실행하지 않는다.

저장된 handoff draft는 아래 API로 승인/반려할 수 있다.

```txt
POST /api/v1/handoff-package-drafts/{draft_id}/approve
POST /api/v1/handoff-package-drafts/{draft_id}/reject
```

approve/reject도 `X-Company-Id` header가 필요하며, draft의 `company_id`와 일치하지 않으면 `403 Forbidden`으로 차단한다.
승인/반려는 review decision만 저장한다.
승인 후에도 `transferred_at=null`을 유지하며 전문가 자동 전달, 외부 export, 정부 제출, 메시지 발송은 실행하지 않는다.
이미 승인/반려된 draft를 다시 처리하면 `409 Conflict`로 응답한다.
approve/reject 응답에는 전체 `package_json`, `worker_id` 원문, worker reply 원문, `translated_ko` 전문, 메시지 전문, 개인정보 원문을 포함하지 않는다.

### 다음 작업

1. DB 문서의 Current SQLite MVP / Planned Context Tables 구분 유지
2. Context tables 설계 및 State Loader DB 전환 계획 수립
3. workers 테이블/조회 기능 설계
4. `worker_name` 기반 `worker_id` lookup 연결
5. 저장된 contact message 조회 API 구현
6. 승인 후 발송/상태 반영 apply 흐름 설계
7. Frontend Dashboard 연결
