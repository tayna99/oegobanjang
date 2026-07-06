# safety_notice_cases

이 문서는 `data-pipeline/seed/synthetic_cases.jsonl`에 들어가는 합성 케이스를 사람이 읽기 쉽게 정리한 raw 시나리오 문서입니다.

주의:

- 모든 케이스는 합성 데이터입니다.
- 공식 근거가 아닙니다.
- evidence_grade는 F입니다.
- 법적 판단 근거로 사용하지 않습니다.

---

# synthetic-vi-002

- case_type: safety_training_notice
- visa_type: E-9
- language_code: vi
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

베트남 근로자에게 제조업 안전교육 참석 안내 메시지 초안을 생성한다.

## input_request

{training_date}에 {training_location}에서 열리는 제조업 안전교육 참석 안내를 베트남어로 작성해줘.

## expected_flow

- generate_korean_original
- generate_vietnamese_message
- include_training_date
- include_training_location
- require_manager_approval
- create_evidence_log

## expected_output

```json
{
  "expected_intent": null,
  "expected_summary": null,
  "expected_status_update": null,
  "required_fields": [
    "worker_name",
    "training_date",
    "training_location",
    "contact_person"
  ],
  "expected_sources": [
    "kosha_manufacturing_safety_vi",
    "kosha_safety_pocketbook_vi"
  ]
}
```

## notes

합성 케이스. 안전교육 메시지 생성 흐름 검증용.

---

# synthetic-id-002

- case_type: safety_training_notice
- visa_type: E-9
- language_code: id
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

인도네시아 근로자에게 제조업 안전교육 참석 안내 메시지 초안을 생성한다.

## input_request

{training_date}에 {training_location}에서 열리는 제조업 안전교육 참석 안내를 인도네시아어로 작성해줘.

## expected_flow

- generate_korean_original
- generate_indonesian_message
- include_training_date
- include_training_location
- require_manager_approval
- create_evidence_log

## expected_output

```json
{
  "expected_intent": null,
  "expected_summary": null,
  "expected_status_update": null,
  "required_fields": [
    "worker_name",
    "training_date",
    "training_location",
    "contact_person"
  ],
  "expected_sources": [
    "kosha_manufacturing_safety_id",
    "kosha_safety_pocketbook_id"
  ]
}
```

## notes

합성 케이스. 안전교육 메시지 생성 흐름 검증용.
