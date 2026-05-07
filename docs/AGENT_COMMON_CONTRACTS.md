# Agent 공통 계약과 작업 분담

## 1. 목적

이 문서는 인력 확보, 다국어 컨택, 비자·서류, 사람 승인·전문가 전달, 감사 로그·근거 저장 작업자가 함께 따라야 할 공통 계약을 정의한다.

목표는 각 Agent를 독립적으로 개발하되, Aggregator에서 결과가 안전하고 일관되게 합쳐지도록 만드는 것이다.

```txt
사용자 자연어 입력
→ Intent Router
→ Planner
→ State Loader
→ 인력 확보 / 다국어 컨택 / 비자·서류 Agent
→ Aggregator
→ Risk Classifier
→ Human Approval
→ Handoff Package 초안 + Evidence Log
```

외고반장은 외국인 고용 운영 OS다. 비자 신청 대행 서비스, 법률 자문 서비스, 노무 자문 서비스, 정부 포털 자동 제출 도구가 아니다.

## 2. 공통 안전 원칙

모든 작업자는 아래 원칙을 유지해야 한다.

- AI가 비자 가능 여부, 법률·노무 판단, 케이스 완료 여부를 확정하지 않는다.
- 정부 포털에 자동 제출하지 않는다.
- 담당자 승인 없이 메시지, 문자, 카카오톡, 이메일, 전문가 전달 패키지를 발송하지 않는다.
- 근로자 상태 업데이트를 자동 확정하지 않는다.
- Evidence Log에 민감정보 원문을 저장하지 않는다.
- Evidence Log에 `worker_reply` 원문 또는 `translated_ko` 전문을 저장하지 않는다.
- 국적별 선호, 근로자 성실도 점수, 이탈 가능성 예측, 감시 기능을 만들지 않는다.
- 외부 발송, export, 전문가 전달, 최종 상태 전환은 반드시 `approval_required=true`를 반환한다.

## 3. `aggregated_output` Schema

`aggregated_output`은 여러 Agent 결과를 하나의 케이스 결과로 합친 공통 출력이다.

Risk Classifier, Human Approval, Handoff Package, Evidence Log 로직은 이 값을 기준으로 다음 단계를 판단한다.

### 현재 최소 형태

현재 구현은 아래 최소 형태를 이미 지원한다.

```json
{
  "agent_count": 3,
  "agents": [
    "workforce_agent",
    "multilingual_contact_agent",
    "visa_document_agent"
  ],
  "summaries": [
    {
      "agent": "visa_document_agent",
      "summary": "체류만료 D-30 구간입니다."
    }
  ],
  "risk_flags": [
    "D-30 임박",
    "메시지 발송 전 승인 필요"
  ],
  "risk_level": "HIGH",
  "approval_required": true,
  "citation_ids": [
    "gov24_stay_extension"
  ],
  "tool_count": 2,
  "rag_context_count": 1
}
```

### 권장 확장 형태

State Loader, Risk Classifier, Handoff Package, Agent 결과 정규화를 확장할 때는 아래 형태를 기준으로 삼는다.

```json
{
  "request_id": "uuid",
  "agent_count": 3,
  "agents": [
    "workforce_agent",
    "multilingual_contact_agent",
    "visa_document_agent"
  ],
  "summaries": [
    {
      "agent": "visa_document_agent",
      "summary": "서류 누락 및 체류만료 D-30 위험이 있습니다.",
      "status": "completed"
    }
  ],
  "key_findings": [
    {
      "agent": "visa_document_agent",
      "type": "document_gap",
      "message": "여권 사본이 누락되었습니다.",
      "severity": "MEDIUM",
      "citation_ids": [
        "doc_requirement_e9_renewal"
      ]
    }
  ],
  "risk_flags": [
    "D-30 임박",
    "누락 서류 1건",
    "외부 발송 승인 필요"
  ],
  "risk_level": "HIGH",
  "risk_reasons": [
    "체류만료일이 30일 이내입니다.",
    "외국인 근로자 대상 메시지 발송 초안이 포함되어 있습니다."
  ],
  "approval_required": true,
  "approval_reasons": [
    "worker_message_draft",
    "expert_handoff_package_draft"
  ],
  "citation_ids": [
    "gov24_stay_extension",
    "doc_requirement_e9_renewal"
  ],
  "handoff_ready": true,
  "handoff_blockers": [],
  "tool_count": 2,
  "rag_context_count": 1
}
```

### 필드 규칙

| 필드 | 의미 |
|---|---|
| `agent_count` | 결과를 만든 고유 Agent 수 |
| `agents` | 실행 순서 기준 고유 Agent 이름 목록 |
| `summaries` | 각 Agent의 원문 없는 짧은 요약 |
| `key_findings` | handoff와 risk review에 필요한 정규화된 핵심 발견 |
| `risk_flags` | state, agent, tool에서 모은 중복 제거 위험 플래그 |
| `risk_level` | `LOW`, `MEDIUM`, `HIGH` 중 하나 |
| `risk_reasons` | 위험도 산정 이유 |
| `approval_required` | 외부 실행 전 workflow가 멈춰야 하는지 여부 |
| `approval_reasons` | 담당자 승인이 필요한 이유 |
| `citation_ids` | RAG 또는 Tool 근거 source_id 목록 |
| `handoff_ready` | 전문가 전달용 초안을 만들 수 있는지 여부 |
| `handoff_blockers` | handoff 초안 생성을 막는 누락 정보 |
| `tool_count` | 사용된 tool result 수 |
| `rag_context_count` | 사용된 RAG context 수 |

Aggregator는 최종 법률·노무·비자 판단을 하지 않는다. Aggregator의 역할은 결과를 합치고 downstream node가 읽을 수 있게 정렬하는 것이다.

## 4. `risk_level` 기준

`risk_level`은 법적 위험 확정이 아니라 운영상 검토 우선순위다.

### LOW

아래 조건을 모두 만족하면 `LOW`로 본다.

- 단순 정보 조회 또는 공식 근거 요약이다.
- 기한 이슈가 없다.
- 누락 서류나 상태 불일치가 없다.
- 외부 발송, export, handoff, 상태 최종 전환 요청이 없다.
- `approval_required=false`다.

### MEDIUM

아래 중 하나라도 해당하면 `MEDIUM`으로 본다.

- 누락 서류가 있다.
- 근로자 답변에 담당자 검토가 필요하다.
- 번역 품질 검수가 필요하다.
- 상태 업데이트 후보가 생성됐다.
- 메시지 초안 또는 handoff 초안이 있지만 기한이 긴급하지는 않다.
- 공식 근거가 부족해 후속 확인이 필요하다.
- `approval_required=true`지만 긴급 기한이나 차단된 행동은 아니다.

### HIGH

아래 중 하나라도 해당하면 `HIGH`로 본다.

- 체류만료일 또는 제출 기한이 D-30 이내다.
- 제출 기한이 지났다.
- 필수 서류 누락과 임박한 기한이 함께 있다.
- 사용자가 자동 발송, 외부 export, 정부 제출, 전문가 전달을 요청한다.
- 사용자가 AI에게 비자 가능 여부, 법률·노무 판단, 케이스 완료를 확정하라고 요청한다.
- Guardrail 위반으로 차단됐다.
- 어떤 Agent든 명시적인 `HIGH` risk flag를 반환했다.

## 5. `approval_required` 기준

`approval_required=true`는 시스템이 실행을 멈추고 담당자 승인을 기다려야 한다는 뜻이다.

아래 경우에는 반드시 `true`여야 한다.

- 근로자 대상 메시지 초안 생성 또는 발송 요청.
- 문자, 카카오톡, 이메일, push 알림.
- 행정사·노무사 대상 handoff package 전달.
- 외부 export, PDF export, 제출용 문서 생성.
- 정부 포털 제출 요청.
- 케이스 완료 또는 최종 상태 전환.
- `status_update_candidates`를 실제 근로자 상태에 반영하는 작업.
- tool result가 `approval_required=true`인 경우.
- tool result 상태가 `NEEDS_APPROVAL`인 경우.

권장 `approval_reasons` 값:

```txt
worker_message_draft
worker_message_send
expert_handoff_package_draft
expert_handoff_transfer
external_export
government_submission
case_completion
status_update_apply
translation_review
legal_or_visa_judgment_blocked
```

## 6. Handoff Package 초안 Schema

Handoff Package는 전문가 검토용 초안이다. 자동 전달물이 아니며, 실제 전달은 담당자 승인 이후에만 가능하다.

권장 형태:

```json
{
  "package_type": "expert_handoff_draft",
  "case_type": "stay_extension",
  "request_id": "uuid",
  "company_id": "company_id",
  "worker_id": "worker_id",
  "case_summary": {
    "title": "E-9 체류연장 서류 검토 요청",
    "summary": "체류만료가 임박하여 서류 누락 여부 확인이 필요합니다.",
    "risk_level": "HIGH",
    "risk_flags": [
      "D-30 임박",
      "여권 사본 누락"
    ]
  },
  "worker_summary": {
    "masked_worker_id": "worker_***",
    "visa_type": "E-9",
    "stay_expires_at": "2026-06-01",
    "contract_ends_at": "2026-05-25"
  },
  "document_summary": {
    "submitted_documents": [
      "alien_registration_card"
    ],
    "missing_documents": [
      "passport_copy",
      "photo"
    ],
    "candidate_updates": [
      {
        "field": "photo",
        "candidate_status": "pending_until_next_day",
        "is_final": false
      }
    ]
  },
  "contact_summary": {
    "last_contact_summary": "근로자가 사진을 내일 제출하겠다고 응답했습니다.",
    "message_draft_exists": true,
    "raw_worker_reply_included": false,
    "full_translation_included": false
  },
  "evidence": {
    "citation_ids": [
      "gov24_stay_extension",
      "doc_requirement_e9_renewal"
    ],
    "evidence_log_ids": [],
    "not_for_legal_judgment": true
  },
  "approval": {
    "approval_required": true,
    "status": "PENDING",
    "reason": "외부 전문가 전달 전 담당자 승인 필요"
  }
}
```

Handoff Package에는 요약과 마스킹된 운영 정보만 포함한다. 민감정보 원문은 포함하지 않는다.

## 7. Evidence Log 원문 저장 금지 규칙

Evidence Log는 왜 그런 판단을 했는지 남기는 기록이다. 민감한 원문 저장소가 아니다.

### 절대 저장 금지

- 외국인등록번호 원문.
- 여권번호 원문.
- 전화번호 전체.
- 주소 전체.
- 불필요한 생년월일 전체.
- 서류 파일 본문.
- OCR 원문.
- `worker_reply` 원문.
- `translated_ko` 전문.
- 근로자에게 보낼 메시지 전문.
- 상담 내용 전문.
- 계약, 급여, 숙소, 의료 관련 원문.
- API key, `.env` 값, token, secret.

### 저장 가능

- 마스킹된 식별자.
- 서류 종류.
- 서류 보유 여부 또는 누락 여부.
- 상태 후보 요약.
- source_id와 citation_id.
- risk_flags.
- 승인 필요 여부와 승인 상태.
- 처리 시각.
- 원문 없는 짧은 요약.

### 좋은 Evidence 요약 예시

```txt
근로자가 여권 보유 및 사진 추후 제출 의사를 밝혔습니다.
베트남어 서류 요청 메시지 초안이 생성되었습니다.
체류만료 D-30 구간으로 관리자 확인이 필요합니다.
사진 제출 예정 상태 후보가 생성되었습니다.
```

### 나쁜 Evidence 요약 예시

```txt
근로자 답변 원문: Tôi có hộ chiếu, ảnh mai gửi...
번역 전문: 저는 여권이 있고 사진은 내일 보내겠습니다...
메시지 전문: 안녕하세요. 귀하의 여권 사본과 사진을...
여권번호 M12345678 확인됨.
```

## 8. 3인 작업 분담안

세 명이 작업한다면 아래처럼 나누는 것이 가장 안전하다.

### A 담당: State Loader와 DB Context

담당 범위:

- `company_context` 로드.
- `worker_context` 로드.
- `candidate_context` 로드.
- Agent 실행 전에 ID와 context 필드를 정규화.

권장 수정 범위:

```txt
backend/app/agent_runtime/graph/nodes/state_loader.py
backend/app/agent_runtime/schemas/state.py
backend/tests/test_agent_state_loader.py
docs/GRAPH_STATE.md
```

완료 기준:

- Planner와 Executor가 정규화된 context를 state에서 읽을 수 있다.
- 회사, 근로자, 후보자 데이터가 없을 때 structured blocker로 표현된다.
- 민감정보 원문이 Evidence Log에 추가되지 않는다.
- 정상 로드, 누락 데이터, 마스킹 동작 테스트가 있다.

### B 담당: Aggregator와 Risk Classifier

담당 범위:

- `aggregated_output` 확장.
- Agent 결과 병합을 deterministic하게 유지.
- Risk Classifier를 분리하거나 formalize.
- risk_flags, risk_level, approval_reasons 정규화.

권장 수정 범위:

```txt
backend/app/agent_runtime/graph/nodes/aggregator.py
backend/app/agent_runtime/graph/nodes/risk_classifier.py
backend/app/agent_runtime/schemas/state.py
backend/tests/test_agent_aggregator.py
backend/tests/test_agent_workflow.py
```

완료 기준:

- 세 Agent 결과가 안정적인 `aggregated_output` 하나로 합쳐진다.
- `risk_level`이 이 문서의 기준을 따른다.
- 어떤 Agent나 Tool이 승인을 요구하면 `approval_required=true`가 유지된다.
- Risk event가 민감정보 원문 없이 기록된다.
- 기존 workflow 테스트가 계속 통과한다.

### C 담당: Handoff Package, Human Approval, Evidence Log

담당 범위:

- `aggregated_output` 기반 전문가 전달용 초안 생성.
- Human Approval이 외부 전달을 막는지 확인.
- sanitize된 Evidence Log event 저장.
- raw worker reply, translated text, message body가 저장되지 않는지 검증.

권장 수정 범위:

```txt
backend/app/agent_runtime/tools/safe_draft.py
backend/app/agent_runtime/graph/nodes/approval_gate.py
backend/app/services/contact_persistence_service.py
backend/app/models/evidence.py
backend/tests/test_contact_persistence_service.py
backend/tests/test_guardrails.py
docs/HANDOFF.md
docs/EVIDENCE_LOG_SCHEMA.md
```

완료 기준:

- Handoff Package는 초안 상태로만 생성된다.
- 외부 전달은 `approval_required=true`, `PENDING` 상태를 요구한다.
- Evidence Log에는 요약, source_id, risk_flags, 승인 상태만 저장된다.
- raw worker reply와 full translated text가 저장되지 않는다.
- 승인 flow가 자동 발송이나 자동 상태 반영을 하지 않는다.

## 9. 한 명이 작업할 경우

한 명이 전부 작업해도 가능하지만 순서를 지키는 편이 안전하다.

1. `aggregated_output`, approval, risk 계약을 먼저 고정한다.
2. State Loader를 구현한다.
3. Aggregator를 확장한다.
4. Risk Classifier를 추가하거나 formalize한다.
5. `aggregated_output` 기반 Handoff Package 초안을 생성한다.
6. Human Approval Gate가 모든 외부 실행을 막는지 확인한다.
7. Evidence Log sanitize 규칙을 검증한다.
8. backend tests와 functional eval을 실행한다.

Handoff Package는 state, 병합 결과, risk_level, approval_reasons에 의존하므로 가장 먼저 구현하지 않는 편이 좋다.

## 10. 권장 검증 명령

각 작업 범위가 merge될 때 아래를 확인한다.

```bash
uv run pytest backend/tests/test_agent_aggregator.py
uv run pytest backend/tests/test_agent_workflow.py backend/tests/test_guardrails.py
uv run pytest backend/tests/test_contact_persistence_service.py
uv run pytest backend/tests
uv run python scripts/run_evals.py --dataset worker_reply_understanding_cases
```

반드시 유지해야 할 safety invariant:

- 외부 실행 초안은 `approval_required=true`다.
- worker reply 해석은 `manager_review_required=true`다.
- 모든 status update candidate는 `is_final=false`다.
- 어떤 candidate도 status `APPLIED`를 갖지 않는다.
- Evidence Log에 raw `worker_reply`가 없다.
- Evidence Log에 full `translated_ko`가 없다.
- Evidence Log에 근로자-facing 메시지 전문이 없다.
- 자동 발송, 자동 export, 정부 제출, 전문가 전달이 없다.
