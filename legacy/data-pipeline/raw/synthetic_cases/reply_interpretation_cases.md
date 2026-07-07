# reply_interpretation_cases

이 문서는 `data-pipeline/seed/synthetic_cases.jsonl`에 들어가는 합성 케이스를 사람이 읽기 쉽게 정리한 raw 시나리오 문서입니다.

주의:

- 모든 케이스는 합성 데이터입니다.
- 공식 근거가 아닙니다.
- evidence_grade는 F입니다.
- 법적 판단 근거로 사용하지 않습니다.

---

# synthetic-vi-003

- case_type: medical_reply
- visa_type: E-9
- language_code: vi
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

베트남 근로자가 몸이 아파 병원에 가야 한다고 답장함.

## input_request

근로자 답장을 해석하고 담당자에게 한국어 요약과 상태 업데이트 후보를 만들어줘.

## worker_reply

Hôm nay tôi bị đau bụng và cần đi bệnh viện.

## expected_flow

- parse_vietnamese_reply
- summarize_reply_in_korean
- detect_medical_issue
- require_human_review
- create_status_update_candidate
- create_evidence_log

## expected_output

```json
{
  "expected_intent": "medical_issue",
  "expected_summary": "근로자가 오늘 복통이 있어 병원에 가야 한다고 답변했습니다.",
  "expected_status_update": {
    "attendance": "needs_check",
    "support": "medical_support_needed"
  },
  "required_fields": null,
  "expected_sources": null
}
```

## notes

합성 케이스. 의료 이슈는 자동 확정하지 않고 담당자 검토가 필요함.

---

# synthetic-id-003

- case_type: medical_reply
- visa_type: E-9
- language_code: id
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

인도네시아 근로자가 몸이 아파 병원에 가야 한다고 답장함.

## input_request

근로자 답장을 해석하고 담당자에게 한국어 요약과 상태 업데이트 후보를 만들어줘.

## worker_reply

Hari ini saya sakit perut dan perlu pergi ke rumah sakit.

## expected_flow

- parse_indonesian_reply
- summarize_reply_in_korean
- detect_medical_issue
- require_human_review
- create_status_update_candidate
- create_evidence_log

## expected_output

```json
{
  "expected_intent": "medical_issue",
  "expected_summary": "근로자가 오늘 복통이 있어 병원에 가야 한다고 답변했습니다.",
  "expected_status_update": {
    "attendance": "needs_check",
    "support": "medical_support_needed"
  },
  "required_fields": null,
  "expected_sources": null
}
```

## notes

합성 케이스. 의료 이슈는 자동 확정하지 않고 담당자 검토가 필요함.

---

# synthetic-vi-004

- case_type: safety_incident_reply
- visa_type: E-9
- language_code: vi
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

베트남 근로자가 작업 중 손을 다쳤다고 답장함.

## input_request

근로자 답장을 해석하고 안전사고 가능성이 있으면 담당자 검토가 필요하다고 표시해줘.

## worker_reply

Tôi bị thương ở tay khi làm việc.

## expected_flow

- parse_vietnamese_reply
- summarize_reply_in_korean
- detect_possible_workplace_injury
- require_human_review
- create_safety_incident_candidate
- create_evidence_log

## expected_output

```json
{
  "expected_intent": "possible_workplace_injury",
  "expected_summary": "근로자가 작업 중 손을 다쳤다고 답변했습니다.",
  "expected_status_update": {
    "safety_incident": "reported",
    "human_review": "required"
  },
  "required_fields": null,
  "expected_sources": null
}
```

## notes

합성 케이스. 산재/응급 여부는 자동 판단하지 않고 담당자가 확인해야 함.

---

# synthetic-id-004

- case_type: safety_incident_reply
- visa_type: E-9
- language_code: id
- mvp_scope: full_e2e
- approval_required: true
- evidence_grade: F
- not_for_legal_basis: true

## situation

인도네시아 근로자가 작업 중 손을 다쳤다고 답장함.

## input_request

근로자 답장을 해석하고 안전사고 가능성이 있으면 담당자 검토가 필요하다고 표시해줘.

## worker_reply

Tangan saya terluka saat bekerja.

## expected_flow

- parse_indonesian_reply
- summarize_reply_in_korean
- detect_possible_workplace_injury
- require_human_review
- create_safety_incident_candidate
- create_evidence_log

## expected_output

```json
{
  "expected_intent": "possible_workplace_injury",
  "expected_summary": "근로자가 작업 중 손을 다쳤다고 답변했습니다.",
  "expected_status_update": {
    "safety_incident": "reported",
    "human_review": "required"
  },
  "required_fields": null,
  "expected_sources": null
}
```

## notes

합성 케이스. 산재/응급 여부는 자동 판단하지 않고 담당자가 확인해야 함.
