# document_request_cases

이 문서는 `data-pipeline/seed/synthetic_cases.jsonl`에 들어가는 합성 케이스를 사람이 읽기 쉽게 정리한 raw 시나리오 문서입니다.

주의:

- 모든 케이스는 합성 데이터입니다.
- 공식 근거가 아닙니다.
- evidence_grade는 F입니다.
- 법적 판단 근거로 사용하지 않습니다.

---

# synthetic-vi-001

- case_type: document_request_reply
- visa_type: E-9
- language_code: vi
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

E-9 베트남 근로자 체류만료 D-76. 여권 사본과 증명사진이 누락됨.

## input_request

근로자에게 여권 사본과 증명사진을 {due_date}까지 제출하라고 베트남어로 안내해줘.

## worker_reply

Tôi có hộ chiếu rồi, nhưng ảnh thì ngày mai tôi mới gửi được.

## expected_flow

- generate_korean_original
- generate_vietnamese_message
- include_privacy_purpose
- include_due_date
- require_manager_approval
- parse_vietnamese_reply
- summarize_reply_in_korean
- create_document_status_update_candidate
- create_evidence_log

## expected_output

```json
{
  "expected_intent": "partial_document_available",
  "expected_summary": "근로자는 여권을 보유하고 있으며, 증명사진은 내일 제출할 수 있다고 답변했습니다.",
  "expected_status_update": {
    "passport": "confirmed",
    "photo": "pending_tomorrow"
  },
  "required_fields": [
    "worker_name",
    "due_date",
    "documents",
    "privacy_purpose",
    "contact_person"
  ],
  "expected_sources": null
}
```

## notes

합성 케이스. 공식 근거가 아니며 평가/데모/Agent 흐름 검증용.

---

# synthetic-id-001

- case_type: document_request_reply
- visa_type: E-9
- language_code: id
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

E-9 인도네시아 근로자 체류만료 D-76. 여권 사본과 증명사진이 누락됨.

## input_request

근로자에게 여권 사본과 증명사진을 {due_date}까지 제출하라고 인도네시아어로 안내해줘.

## worker_reply

Saya sudah punya paspor, tetapi foto baru bisa saya kirim besok.

## expected_flow

- generate_korean_original
- generate_indonesian_message
- include_privacy_purpose
- include_due_date
- require_manager_approval
- parse_indonesian_reply
- summarize_reply_in_korean
- create_document_status_update_candidate
- create_evidence_log

## expected_output

```json
{
  "expected_intent": "partial_document_available",
  "expected_summary": "근로자는 여권을 보유하고 있으며, 증명사진은 내일 제출할 수 있다고 답변했습니다.",
  "expected_status_update": {
    "passport": "confirmed",
    "photo": "pending_tomorrow"
  },
  "required_fields": [
    "worker_name",
    "due_date",
    "documents",
    "privacy_purpose",
    "contact_person"
  ],
  "expected_sources": null
}
```

## notes

합성 케이스. 공식 근거가 아니며 평가/데모/Agent 흐름 검증용.
