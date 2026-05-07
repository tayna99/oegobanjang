# DB Schema

## 1. 목적

이 문서는 외고반장 MVP에서 필요한 주요 DB 테이블을 정의한다.

정형 상태는 PostgreSQL에 저장한다.  
공식 문서 검색용 데이터는 Chroma에 저장한다.

---

## 2. 설계 원칙

```txt
RAG = 공식 근거와 절차를 찾는 곳
DB = 현재 사업장·직원·후보자·서류·승인 상태를 저장하는 곳
Rule Base = 날짜 계산과 true/false 판단을 하는 곳
```

DB에는 현재 상태와 실행 이력을 저장한다.

RAG에는 법령, 절차, 서식, 안전자료, 메시지 템플릿을 저장한다.

---

## 3. users

관리자 또는 담당자 계정.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 사용자 ID |
| email | varchar | N | 로그인 이메일 |
| password_hash | varchar | N | 비밀번호 해시 |
| name | varchar | N | 사용자 이름 |
| role | varchar | N | ADMIN/MANAGER |
| is_active | boolean | N | 활성 여부 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

---

## 4. companies

사업장 정보.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 사업장 ID |
| name | varchar | N | 사업장명 |
| business_number | varchar | Y | 사업자등록번호 |
| industry | varchar | N | 업종 |
| region | varchar | N | 지역 |
| address | varchar | Y | 주소 |
| current_foreign_workers | int | N | 현재 외국인 근로자 수 |
| housing_available | boolean | Y | 숙소 제공 여부 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

---

## 5. workers

외국인 근로자 정보.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 근로자 ID |
| company_id | UUID | N | 사업장 ID |
| name | varchar | N | 이름 |
| nationality | varchar | N | 국적 |
| preferred_language | varchar | Y | 선호 언어 |
| visa_type | varchar | N | 체류자격 |
| visa_expires_at | date | N | 체류만료일 |
| contract_starts_at | date | Y | 계약시작일 |
| contract_ends_at | date | Y | 계약종료일 |
| status | varchar | N | ACTIVE/INACTIVE/LEFT/PENDING |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

민감정보인 여권번호, 외국인등록번호는 별도 보안 테이블 또는 암호화 필드로 분리한다.

---

## 6. worker_sensitive_profiles

근로자 민감정보.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 민감정보 ID |
| worker_id | UUID | N | 근로자 ID |
| passport_number_encrypted | varchar | Y | 암호화된 여권번호 |
| alien_registration_number_encrypted | varchar | Y | 암호화된 외국인등록번호 |
| phone_number_encrypted | varchar | Y | 암호화된 연락처 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

---

## 7. candidates

신규 채용 후보자 정보.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 후보자 ID |
| company_id | UUID | N | 사업장 ID |
| nationality | varchar | N | 국적 |
| visa_type | varchar | Y | 예상 체류자격 |
| passport_ready | boolean | N | 여권 준비 여부 |
| photo_ready | boolean | N | 사진 준비 여부 |
| health_check_ready | boolean | N | 건강검진 준비 여부 |
| available_start_date | date | Y | 근무 가능일 |
| status | varchar | N | PENDING/READY/NEEDS_INFO/REJECTED |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

후보자는 추천 대상이 아니라 준비 상태 확인 대상이다.

---

## 8. hiring_requests

신규 인력 요청.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 채용 요청 ID |
| company_id | UUID | N | 사업장 ID |
| requested_count | int | N | 요청 인원 |
| visa_type | varchar | N | 요청 체류자격 |
| nationality_preference_note | text | Y | 국적 관련 입력 원문 보관 주의 |
| job_description | text | Y | 직무 설명 |
| housing_required | boolean | Y | 숙소 필요 여부 |
| status | varchar | N | DRAFT/PENDING_REVIEW/APPROVED/CANCELLED |
| created_by | UUID | N | 생성자 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

국적별 선호 또는 차별적 추천은 금지한다. 입력값은 검토가 필요하다.

---

## 9. visas

비자/체류 상태.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 비자 상태 ID |
| worker_id | UUID | N | 근로자 ID |
| visa_type | varchar | N | 체류자격 |
| issued_at | date | Y | 발급일 |
| expires_at | date | N | 만료일 |
| status | varchar | N | ACTIVE/EXPIRING/EXPIRED/REVIEW_REQUIRED |
| last_checked_at | timestamp | Y | 마지막 확인일 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

D-day는 저장해도 되지만, 기본적으로 날짜 기반 Rule Base에서 계산한다.

---

## 10. document_requirements

케이스별 필수 서류 기준.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 기준 ID |
| case_type | varchar | N | stay_extension/new_hiring/employment_change 등 |
| visa_type | varchar | N | E-9 등 |
| required_doc | varchar | N | 필수 서류 코드 |
| required | boolean | N | 필수 여부 |
| source_id | varchar | N | 근거 문서 source_id |
| notes | text | Y | 설명 |
| created_at | timestamp | N | 생성일 |

초기에는 CSV로 관리하다가 DB로 옮길 수 있다.

---

## 11. worker_documents

근로자별 제출 서류 상태.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 문서 ID |
| worker_id | UUID | N | 근로자 ID |
| doc_type | varchar | N | 문서 종류 |
| status | varchar | N | MISSING/SUBMITTED/REVIEWED/EXPIRED |
| file_path | varchar | Y | 파일 경로 |
| submitted_at | timestamp | Y | 제출일 |
| reviewed_at | timestamp | Y | 검토일 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |

---

## 12. contact_messages

다국어 메시지 초안 및 승인 이후 발송 이력.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 메시지 ID |
| worker_id | UUID | Y | 대상 근로자 |
| message_purpose | varchar | N | safety_training_notice/counseling_center_guide/passport_request 등 |
| language_code | varchar | N | MVP는 vi/id 중심 |
| korean_text | text | N | 한국어 원문 |
| translated_text | text | Y | 번역 초안 |
| status | varchar | N | DRAFT/PENDING_APPROVAL/APPROVED/SENT/CANCELLED |
| approval_required | boolean | N | 발송 전 승인 필요 여부 |
| approval_id | UUID | Y | 승인 ID |
| citation_source_ids | jsonb | Y | RAG 근거 source_id 목록 |
| risk_flags | jsonb | Y | 안전 플래그 |
| created_by | UUID | N | 생성자 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |
| sent_at | timestamp | Y | 발송일 |

상태 예시:

```txt
DRAFT
PENDING_APPROVAL
APPROVED
SENT
CANCELLED
```

초안 생성 시 기본 상태:

```txt
status=PENDING_APPROVAL
approval_required=true
sent_at=null
```

`korean_text`와 `translated_text`는 담당자 검토가 필요한 운영 데이터이므로 저장한다.
단, 이 데이터는 발송 전 초안이며 실제 발송은 승인 이후 별도 단계에서만 가능하다.

자동 발송은 금지한다.

---

## 13. approvals

관리자 승인 상태.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 승인 ID |
| target_type | varchar | N | contact_message/status_update_candidate 등 승인 대상 유형 |
| target_id | UUID | N | 승인 대상 ID |
| status | varchar | N | PENDING/APPROVED/REJECTED/CANCELLED |
| requested_by | UUID | Y | 요청자 |
| reviewed_by | UUID | Y | 검토자 |
| created_at | timestamp | N | 생성일 |
| reviewed_at | timestamp | Y | 검토일 |
| reason | text | Y | 승인 필요 사유 |

상태 예시:

```txt
PENDING
APPROVED
REJECTED
CANCELLED
```

`target_type`/`target_id`는 `contact_messages`, `status_update_candidates` 등 승인 대상과 연결한다.

메시지 발송과 상태 반영은 `status=APPROVED` 이후 별도 실행 단계에서만 가능하다.

---

## 14. handoff_package_drafts

전문가 검토용 handoff package 초안.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 초안 ID |
| request_id | UUID | Y | Runtime 요청 ID |
| company_id | UUID | Y | 접근 scope. MVP에서는 X-Company-Id와 비교 |
| package_type | varchar | N | expert_handoff_draft |
| case_type | varchar | Y | stay_extension 등 |
| worker_id | UUID | Y | 내부 relation용. package_json에는 저장하지 않음 |
| masked_worker_id | varchar | N | 응답/요약용 마스킹 ID |
| risk_level | varchar | Y | LOW/MEDIUM/HIGH |
| handoff_ready | boolean | N | 전문가 검토 초안 준비 가능 여부 |
| handoff_blockers | text | Y | JSON string |
| package_json | text | N | allowlist 기반 sanitize JSON string |
| approval_required | boolean | N | 승인 필요 여부 |
| approval_id | UUID | Y | 승인 ID |
| status | varchar | N | PENDING_APPROVAL/APPROVED/REJECTED |
| created_by | UUID | Y | 생성 요청자 |
| created_at | timestamp | N | 생성일 |
| updated_at | timestamp | N | 수정일 |
| transferred_at | timestamp | Y | 전문가 전달 시각. 초안 생성/승인 시에는 null |

초기 상태:

```txt
status=PENDING_APPROVAL
approval_required=true
approval.status=PENDING
transferred_at=null
```

승인/반려 상태 전이:

```txt
approve:
handoff_package_drafts.status=PENDING_APPROVAL → APPROVED
approvals.status=PENDING → APPROVED
transferred_at=null 유지

reject:
handoff_package_drafts.status=PENDING_APPROVAL → REJECTED
approvals.status=PENDING → REJECTED
transferred_at=null 유지
```

이미 `APPROVED` 또는 `REJECTED`인 draft는 다시 처리하지 않는다.

`package_json` 저장 허용:

- 요약
- masked_worker_id
- visa_type
- stay_expires_at
- contract_ends_at
- 서류 종류와 누락 여부
- 상태 후보 요약
- citation_ids
- evidence_log_ids
- risk_flags
- approval_required
- approval.status=PENDING
- not_for_legal_judgment=true

`package_json` 저장 금지:

- worker_id 원문
- worker_name 원문
- nationality
- worker_reply 원문
- translated_ko 전문
- 근로자-facing message body 전문
- 여권번호 원문
- 외국인등록번호 원문
- 전화번호 전체
- 주소 전체
- 문서/OCR 원문
- 법률·노무 판단 확정 문장
- 비자 가능 여부 확정 문장

`company_id`는 접근 제어용 scope다.
`created_by`는 생성 요청 사용자이고, `worker_id`는 내부 relation이다.
MVP/demo 조회 API는 `X-Company-Id` header와 `handoff_package_drafts.company_id`를 비교한다.
운영 전에는 인증 토큰 기반 company membership/role 검증으로 교체해야 한다.

실제 전문가 전달은 `status=APPROVED` 이후에도 별도 실행 단계에서만 가능하다.

---

## 15. evidence_logs

AI 판단 근거와 실행 이력.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 로그 ID |
| request_id | UUID | N | 요청 ID |
| worker_id | UUID | Y | 근로자 ID |
| agent_name | varchar | N | Agent 이름 |
| event_type | varchar | N | 이벤트 유형 |
| tool_name | varchar | Y | 실행 Tool |
| summary | text | N | 원문 없는 이벤트 요약 |
| source_ids | jsonb | Y | 근거 source_id 목록 |
| approval_required | boolean | N | 승인 필요 여부 |
| risk_flags | jsonb | Y | 안전 플래그 |
| contact_message_id | UUID | Y | 관련 메시지 초안 ID |
| status_update_candidate_id | UUID | Y | 관련 상태 후보 ID |
| approval_id | UUID | Y | 승인 ID |
| created_at | timestamp | N | 생성일 |

다국어 Contact Agent 주요 event_type:

```txt
rag_retrieved
message_draft_created
approval_requested
worker_reply_summarized
status_update_candidate_created
```

저장 가능:

- 원문 없는 요약
- source_id 목록
- approval_required
- risk_flags
- candidate 상태 요약

저장 금지:

- 메시지 전문
- worker_reply 원문
- 여권번호
- 외국인등록번호
- 전화번호 전체
- 주소 전체
- 기타 개인정보 원문

`summary`에는 원문이 아니라 요약만 저장한다.

예:

```txt
message_draft_created → 베트남어 안전교육 안내 메시지 초안이 생성됨
worker_reply_summarized → 근로자가 여권 보유 및 사진 추후 제출 의사를 밝힘
```

민감정보 원문은 저장하지 않는다.

---

## 16. status_update_candidates

근로자 답변에서 추출한 상태 업데이트 후보.

| column | type | nullable | description |
|---|---|---:|---|
| id | UUID | N | 상태 후보 ID |
| worker_id | UUID | N | 근로자 ID |
| target_type | varchar | N | worker_document/worker_profile/support_case 등 |
| target_key | varchar | N | passport/photo/expected_submission_date 등 |
| candidate_status | varchar | N | available/pending_until_next_day/needs_review 등 |
| confidence | varchar | Y | LOW/MEDIUM/HIGH 또는 nullable |
| manager_review_required | boolean | N | 담당자 검토 필요 여부 |
| status | varchar | N | PENDING_REVIEW/APPROVED/REJECTED/APPLIED |
| source_message_id | UUID | Y | 관련 contact_messages ID |
| approval_id | UUID | Y | 승인 ID |
| created_at | timestamp | N | 생성일 |
| reviewed_at | timestamp | Y | 검토일 |

상태 예시:

```txt
PENDING_REVIEW
APPROVED
REJECTED
APPLIED
```

상태 업데이트 후보 생성 시 기본 상태:

```txt
status=PENDING_REVIEW
manager_review_required=true
```

실제 `worker_documents` 상태를 바로 변경하지 않는다.
승인 후 별도 apply 단계에서만 반영한다.

---

## 17. rag_sources

RAG 원천 문서 메타데이터.

| column | type | nullable | description |
|---|---|---:|---|
| source_id | varchar | N | 문서 source_id |
| title | varchar | N | 제목 |
| publisher | varchar | N | 발행기관 |
| source_type | varchar | N | official_law/procedure/form 등 |
| url | text | Y | 원문 URL |
| retrieved_at | date | N | 수집일 |
| effective_date | date | Y | 시행일 |
| evidence_grade | varchar | N | A/B/C/D/E/F |
| created_at | timestamp | N | 생성일 |

Vector 자체는 Chroma에 저장하고, 메타데이터는 필요하면 PostgreSQL에도 저장한다.

---

## 18. 초기 Seed 파일

```txt
data-pipeline/seed/companies.csv
data-pipeline/seed/employees.csv
data-pipeline/seed/candidates.csv
data-pipeline/seed/document_requirements.csv
data-pipeline/seed/visa_lookup.csv
data-pipeline/seed/country_lookup.csv
data-pipeline/seed/message_templates.csv
```

---

## 19. 향후 검토

- Refresh token/session 관리가 필요하면 auth_sessions 추가
- 파일 업로드가 본격화되면 files 테이블 추가
- 장기 스케줄링이 필요하면 scheduled_jobs 테이블 추가
- 인터뷰 기반 케이스가 쌓이면 case_examples 테이블 추가
