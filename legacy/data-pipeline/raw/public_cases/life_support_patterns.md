# life_support_patterns

이 문서는 `data-pipeline/seed/public_case_patterns.jsonl`에 들어가는 공개 상담 사례 패턴을 사람이 읽기 쉽게 정리한 raw 문서입니다.

주의:

- 상담 원문을 저장하지 않습니다.
- 사람 이름, 회사명, 전화번호, 주소, 구체적 사건을 저장하지 않습니다.
- 문제 유형, 근로자가 원하는 도움, 메시지 톤, 다음 행동 후보만 저장합니다.
- evidence_grade는 D입니다.
- 법적 판단 근거로 사용하지 않습니다.

---

# public-pattern-housing

- case_type: housing_issue
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

기숙사 생활 규칙이나 불편사항 문의

## typical_worker_need

기숙사 규칙, 문제 발생 시 연락처, 담당자 확인 방법을 알고 싶어함

## suggested_message_tone

책임 추궁보다 생활 안내와 연락 방법 중심

## next_action_candidates

- provide_housing_notice_draft
- guide_contact_person
- ask_issue_category
- require_manager_review

## notes

기숙사 관련 실제 분쟁 원문 저장 금지. 유형과 대응 후보만 저장.

---

# public-pattern-medical-support

- case_type: medical_support
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

근로자가 아프거나 다쳐서 병원, 약국, 응급 연락 방법을 문의하는 상황

## typical_worker_need

병원 방문 가능 여부, 담당자 보고 방법, 응급상황 시 119 연락 여부를 알고 싶어함

## suggested_message_tone

불안감을 줄이고 즉시 연락해야 할 대상을 명확히 안내하는 톤

## next_action_candidates

- summarize_medical_reply
- guide_contact_person
- guide_emergency_119_if_needed
- create_medical_support_status_candidate
- require_manager_review

## notes

의료적 진단/처방 금지. 담당자 확인과 공식 의료기관 이용 안내에만 사용.

---

# public-pattern-wage-delay

- case_type: wage_delay
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

근로자가 급여 지급일이 지났는데 임금을 받지 못했거나 금액을 확인하고 싶어하는 상황

## typical_worker_need

급여 지급일, 입금 여부, 급여명세서, 담당자 확인 또는 상담센터 문의가 필요함

## suggested_message_tone

단정하거나 법적 판단하지 않고 사실 확인과 상담 연결을 돕는 톤

## next_action_candidates

- ask_payday_and_payment_status
- guide_contact_person
- guide_counseling_center_if_needed
- require_manager_review

## notes

임금체불 법적 판단 근거로 사용하지 않음. 공식 상담/담당자 확인 안내용.

---

# public-pattern-counseling-center-question

- case_type: counseling_center_question
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

근로자가 문제 발생 시 어디에 문의해야 하는지 묻는 상황

## typical_worker_need

상담센터 전화번호, 상담 가능 주제, 담당자 연락 방법을 알고 싶어함

## suggested_message_tone

공식 문의처와 담당자 확인 방법을 간단히 안내하는 톤

## next_action_candidates

- generate_counseling_center_guide
- include_center_phone
- include_contact_person
- require_manager_approval

## notes

외국인력상담센터 및 지자체 센터 안내와 연결.

---

# public-pattern-transportation-question

- case_type: transportation_question
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

근로자가 출근 교통편, 교통카드, 버스/지하철 이용 방법을 문의하는 상황

## typical_worker_need

출근 방법, 교통카드 사용, 담당자에게 확인해야 할 장소 정보를 알고 싶어함

## suggested_message_tone

짧고 실용적으로 이동 방법과 확인할 정보를 안내하는 톤

## next_action_candidates

- provide_transportation_notice_draft
- include_workplace_location
- include_contact_person
- require_manager_review

## notes

실시간 교통 정보가 아니라 일반 안내 패턴. 최신 노선/요금은 별도 확인 필요.
