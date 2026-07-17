"""Planner — LLM이 아니라 코드 dict (발표 p.16 "라우팅 매핑은 코드 검토만으로 다 보여야 함").

legacy services/daily_briefing_planner.py:160-250 이식. intent별 실행 계획 스텝과
필요한 컨텍스트 스냅샷 종류를 고정한다 — backend context_service(G2)가
REQUIRED_CONTEXT_BY_INTENT를 보고 ContextSnapshot을 조립한다.
"""

from __future__ import annotations

PLAN_STEPS_BY_INTENT: dict[str, list[str]] = {
    "daily_briefing": [
        "load_company_worker_document_state",
        "evaluate_rule_based_daily_risks",
        "validate_citations",
        "create_pending_next_actions",
        "return_approval_ready_briefing",
    ],
    "visa_expiry": [
        "resolve_worker_reference",
        "load_worker_state",
        "evaluate_visa_expiry",
        "check_missing_renewal_documents",
        "create_pending_next_actions",
    ],
    "document_gap": [
        "load_company_worker_document_state",
        "evaluate_missing_required_documents",
        "create_document_request_actions",
        "return_approval_ready_briefing",
    ],
    "contract_visa_conflict": [
        "load_worker_contract_and_visa_dates",
        "evaluate_contract_visa_conflict",
        "flag_expert_review_if_needed",
        "create_pending_next_actions",
    ],
    "reporting_deadline": [
        "load_reporting_events",
        "evaluate_reporting_deadlines",
        "flag_overdue_or_urgent_reports",
        "create_pending_next_actions",
    ],
    "quota_review": [
        "load_company_quota_state",
        "evaluate_quota_review_need",
        "prepare_readiness_checklist",
        "create_pending_next_actions",
    ],
    "handoff_preview": [
        "resolve_case_or_worker_reference",
        "load_risk_and_citation_context",
        "create_handoff_preview",
        "return_internal_preview_only",
    ],
    "document_request_message": [
        "load_missing_document_cases",
        "prepare_multilingual_document_request_draft",
        "mark_external_send_as_approval_required",
        "return_preview_only_message_action",
    ],
    "contact_onboarding": [
        "extract_contact_context",
        "prepare_multilingual_onboarding_draft",
        "mark_external_send_as_approval_required",
        "return_preview_only_message_action",
    ],
    "worker_reply_interpretation": [
        "extract_worker_reply",
        "summarize_worker_reply",
        "create_status_update_candidates",
        "mark_status_update_as_approval_required",
    ],
    "candidate_readiness": [
        "load_candidate_document_state",
        "check_required_candidate_documents",
        "return_readiness_gaps_without_scores",
        "create_pending_next_actions",
    ],
    "evidence_audit_review": [
        "load_recent_evidence_events",
        "link_cases_to_citations",
        "return_reproducible_audit_trace",
    ],
}

REQUIRED_CONTEXT_BY_INTENT: dict[str, list[str]] = {
    "daily_briefing": ["company", "workers", "documents", "citations", "approvals"],
    "visa_expiry": ["company", "workers", "documents", "citations"],
    "document_gap": ["company", "workers", "documents", "citations"],
    "contract_visa_conflict": ["company", "workers", "contracts", "citations"],
    "reporting_deadline": ["company", "workers", "reporting_events", "citations"],
    "quota_review": ["company", "quota", "workers", "citations"],
    "handoff_preview": ["company", "cases", "actions", "citations", "approvals"],
    "document_request_message": ["company", "workers", "documents", "messages", "approvals"],
    "contact_onboarding": ["company", "workers", "messages", "approvals"],
    "worker_reply_interpretation": ["company", "workers", "messages", "approvals"],
    "candidate_readiness": ["company", "candidates", "candidate_documents", "citations"],
    "evidence_audit_review": ["company", "cases", "citations", "evidence_events"],
}
