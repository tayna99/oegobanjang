# safety_patterns

이 문서는 `data-pipeline/seed/public_case_patterns.jsonl`에 들어가는 공개 상담 사례 패턴을 사람이 읽기 쉽게 정리한 raw 문서입니다.

주의:

- 상담 원문을 저장하지 않습니다.
- 사람 이름, 회사명, 전화번호, 주소, 구체적 사건을 저장하지 않습니다.
- 문제 유형, 근로자가 원하는 도움, 메시지 톤, 다음 행동 후보만 저장합니다.
- evidence_grade는 D입니다.
- 법적 판단 근거로 사용하지 않습니다.

---

# public-pattern-safety-training

- case_type: safety_training_question
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

근로자가 안전교육 일정, 장소, 준비물을 문의하는 상황

## typical_worker_need

교육 일시, 장소, 준비물, 담당자 연락처를 명확히 알고 싶어함

## suggested_message_tone

짧고 명확하게 일정과 장소를 안내하는 톤

## next_action_candidates

- generate_safety_training_notice
- include_training_date
- include_training_location
- include_contact_person
- require_manager_approval

## notes

KOSHA 안전자료와 연결 가능한 상담 유형 패턴. 법적/사고 책임 판단 근거로 사용하지 않음.

---

# public-pattern-workplace-injury

- case_type: possible_workplace_injury
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

근로자가 작업 중 다쳤거나 안전사고 가능성이 있는 상황을 알리는 경우

## typical_worker_need

응급 조치, 담당자 보고, 병원 방문, 사고 내용 전달 방법을 알고 싶어함

## suggested_message_tone

사고 책임 판단을 하지 않고 안전 확보와 담당자 보고를 우선하는 톤

## next_action_candidates

- detect_possible_workplace_injury
- summarize_reply_in_korean
- create_safety_incident_candidate
- require_human_review
- create_evidence_log

## notes

산재 여부, 책임 소재, 법적 판단을 자동으로 확정하지 않음.
