# document_patterns

이 문서는 `data-pipeline/seed/public_case_patterns.jsonl`에 들어가는 공개 상담 사례 패턴을 사람이 읽기 쉽게 정리한 raw 문서입니다.

주의:

- 상담 원문을 저장하지 않습니다.
- 사람 이름, 회사명, 전화번호, 주소, 구체적 사건을 저장하지 않습니다.
- 문제 유형, 근로자가 원하는 도움, 메시지 톤, 다음 행동 후보만 저장합니다.
- evidence_grade는 D입니다.
- 법적 판단 근거로 사용하지 않습니다.

---

# public-pattern-document-delay

- case_type: document_delay
- target_languages: vi, id
- mvp_priority: vi_id_full_service
- evidence_grade: D
- not_for_legal_basis: true
- source_status: pattern_summary_only

## issue

근로자가 요청받은 서류를 기한 내 제출하지 못하는 상황

## typical_worker_need

어떤 서류를 제출해야 하는지, 원본인지 사진인지, 언제까지 제출해야 하는지 다시 확인해야 함

## suggested_message_tone

비난하지 않고 필요한 서류와 제출 가능일을 확인하는 톤

## next_action_candidates

- request_missing_document_again
- ask_expected_submission_date
- create_document_status_update_candidate
- require_manager_review

## notes

상담 원문이 아니라 유형화된 패턴. 실제 사람/회사/사건 정보 저장 금지.
