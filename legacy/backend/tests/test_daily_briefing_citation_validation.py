from types import SimpleNamespace

from app.services.daily_briefing_service import (
    DailyBriefingService,
    build_seed_daily_briefing_service,
    build_seed_repository,
)


class FakeRetrievalResult:
    def __init__(self, *source_ids: str):
        self.found = bool(source_ids)
        self.citations = [
            SimpleNamespace(
                source_id=source_id,
                title=f"Official source for {source_id}",
                publisher="Official",
                url=f"https://example.test/{source_id}",
                evidence_grade="A",
                excerpt="official evidence excerpt",
            )
            for source_id in source_ids
        ]


class FakeRetriever:
    def __init__(self, matched_source_ids: set[str]):
        self.matched_source_ids = matched_source_ids
        self.queries: list[str] = []

    def search(self, query: str, **kwargs):
        self.queries.append(query)
        for source_id in sorted(self.matched_source_ids):
            if source_id in query:
                return FakeRetrievalResult(source_id)
        return FakeRetrievalResult()


def test_daily_briefing_validates_citations_against_retriever():
    service = build_seed_daily_briefing_service(
        citation_retriever=FakeRetriever(
            {
                "cit_visa_expiry",
                "cit_missing_document",
                "cit_contract_visa_conflict",
                "cit_reporting_deadline",
                "cit_quota_review",
            }
        )
    )

    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")

    assert result.citation_summaries
    assert {summary.validation_status for summary in result.citation_summaries} == {
        "validated"
    }
    assert all(not summary.missing_evidence for summary in result.citation_summaries)
    assert any(
        event.event_type == "citation_validated"
        for event in service.repository.evidence_events.values()
    )


def test_missing_rag_citation_marks_missing_evidence_and_preview_warning():
    service = build_seed_daily_briefing_service(citation_retriever=FakeRetriever(set()))

    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")

    assert result.citation_summaries
    assert {summary.validation_status for summary in result.citation_summaries} == {
        "missing_evidence"
    }
    assert all(summary.missing_evidence for summary in result.citation_summaries)

    handoff_actions = [
        action
        for action in result.recommended_actions
        if action.action_type == "create_handoff"
    ]
    assert handoff_actions
    preview = service.get_handoff_preview(
        handoff_actions[0].action_id,
        allowed_company_ids=["company_001"],
    )
    assert "missing_evidence" in preview.warning_flags
    assert any(
        event.event_type == "citation_missing_evidence"
        for event in service.repository.evidence_events.values()
    )


def test_stale_official_citation_is_blocked_even_when_retrieved():
    repository = build_seed_repository()
    repository.citations["cit_visa_expiry"].ingest_at = "2025-01-01T00:00:00+09:00"
    service = DailyBriefingService(
        repository,
        citation_retriever=FakeRetriever({"cit_visa_expiry"}),
    )

    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    summary = next(
        citation
        for citation in result.citation_summaries
        if citation.citation_id == "cit_visa_expiry"
    )

    assert summary.validation_status == "stale_evidence"
    assert summary.stale_evidence is True
    assert summary.missing_evidence is True
    assert summary.policy_update_needed is True


def test_synthetic_only_citation_is_blocked_even_when_retrieved():
    repository = build_seed_repository()
    repository.citations["cit_missing_document"].source_type = "synthetic"
    service = DailyBriefingService(
        repository,
        citation_retriever=FakeRetriever({"cit_missing_document"}),
    )

    result = service.run_daily_briefing("company_001", "2026-05-08", user_role="manager")
    summary = next(
        citation
        for citation in result.citation_summaries
        if citation.citation_id == "cit_missing_document"
    )

    assert summary.validation_status == "synthetic_only"
    assert summary.synthetic_only is True
    assert summary.missing_evidence is True
