import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import create_app


def _bearer_token(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}

    def encode(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    signing_input = f"{encode(header)}.{encode(payload)}"
    signature = hmac.new(
        b"change-this-local-secret",
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{signing_input}.{encoded_signature}"


def _restore_canonical_visa_citation(client: TestClient) -> None:
    client.post(
        "/api/v1/daily-briefings/sources/import",
        json={
            "citations": [
                {
                    "citation_id": "cit_visa_expiry",
                    "title": "Visa expiry official guidance",
                    "source_type": "official",
                    "source": "HiKorea mock official guidance for visa expiry renewal timing.",
                    "ingest_at": "2026-05-01T00:00:00+09:00",
                    "document_id": "doc_visa_expiry",
                    "chunk_id": "chunk_visa_expiry",
                    "chunk_version": "2026-05-01",
                    "retrieved_at": "2026-05-08T00:00:00+09:00",
                    "source_url": "mock://official/visa-expiry",
                }
            ]
        },
        headers={"X-User-Role": "admin"},
    )


def test_daily_briefing_api_returns_embedded_citation_summaries() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["briefing_run_id"] == "brf_company_001_2026-05-08"
    assert body["risk_summary"]["total_count"] == 6
    assert body["risk_summary"]["by_risk_type"]["contract_visa_conflict"] == 1
    assert body["risk_summary"]["by_risk_type"]["reporting_deadline"] == 1
    assert body["risk_summary"]["by_risk_type"]["quota_review"] == 1
    assert body["citation_summaries"]
    assert body["approval_required"] is True


def test_daily_briefing_api_allows_omitted_date_with_company_timezone_today() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["date"]
    assert body["briefing_run_id"].startswith("brf_company_001_")


def test_approval_api_requires_manager_or_admin() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    approval_id = briefing["recommended_actions"][0]["approval_id"]

    denied = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers={"X-Company-Id": "company_001", "X-User-Role": "viewer", "X-User-Id": "viewer_001"},
    )

    assert denied.status_code == 403
    assert denied.json()["detail"]["error_code"] == "UNAUTHORIZED_ROLE"

    approved = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_daily_briefing_detail_and_case_evidence_api() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()

    detail = client.get(f"/api/v1/daily-briefings/{briefing['briefing_run_id']}")
    evidence = client.get(f"/api/v1/cases/{briefing['items'][0]['case_id']}/evidence-events")

    assert detail.status_code == 200
    assert detail.json()["briefing_run_id"] == briefing["briefing_run_id"]
    assert evidence.status_code == 200
    assert any(event["event_type"] == "risk_flagged" for event in evidence.json())


def test_case_audit_review_api_returns_reproducible_bundle() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    item = briefing["items"][0]

    response = client.get(
        f"/api/v1/cases/{item['case_id']}/audit-review",
        headers={"X-Company-Id": "company_001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["case_id"] == item["case_id"]
    assert body["rule_snapshot"]["risk_type"] == item["risk_type"]
    assert body["source_snapshot_hash"] == briefing["source_snapshot_hash"]
    assert body["evidence_events"]
    assert body["approval_history"]
    assert body["citation_details"]
    assert "Nguyen Van A" not in str(body)


def test_case_audit_review_api_respects_tenant_scope() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()

    response = client.get(
        f"/api/v1/cases/{briefing['items'][0]['case_id']}/audit-review",
        headers={"X-Company-Id": "other_company"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_citation_detail_api_returns_source_metadata() -> None:
    client = TestClient(create_app())
    _restore_canonical_visa_citation(client)
    client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    response = client.get("/api/v1/citations/cit_visa_expiry")

    assert response.status_code == 200
    body = response.json()
    assert body["citation_id"] == "cit_visa_expiry"
    assert body["source_type"] == "official"
    assert body["title"]
    assert body["ingest_at"]
    assert body["document_id"] == "doc_visa_expiry"
    assert body["chunk_id"] == "chunk_visa_expiry"
    assert body["chunk_version"] == "2026-05-01"
    assert body["retrieved_at"]
    assert body["source_url"].startswith("mock://")
    assert body["stale_evidence"] is False


def test_source_import_api_upserts_operational_daily_briefing_sources() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/sources/import",
        json={
            "companies": [
                {
                    "company_id": "company_imported",
                    "company_name": "Imported Company",
                    "timezone": "Asia/Seoul",
                    "quota_limit": 1,
                    "current_foreign_worker_count": 1,
                }
            ],
            "workers": [
                {
                    "worker_id": "worker_imported_001",
                    "company_id": "company_imported",
                    "display_name_masked": "[WORKER_IMPORTED_001]",
                    "raw_name": "Imported Private Name",
                    "visa_expiry_date": "2026-05-20",
                    "contract_end_date": "2026-06-30",
                }
            ],
            "documents": [
                {
                    "worker_id": "worker_imported_001",
                    "document_type": "passport_copy",
                    "status": "missing",
                    "required": True,
                    "due_date": "2026-05-09",
                }
            ],
            "citations": [
                {
                    "citation_id": "cit_visa_expiry",
                    "title": "Imported visa citation",
                    "source_type": "official",
                    "source": "Imported official source",
                    "ingest_at": "2026-05-01T00:00:00+09:00",
                },
                {
                    "citation_id": "cit_missing_document",
                    "title": "Imported document citation",
                    "source_type": "official",
                    "source": "Imported official source",
                    "ingest_at": "2026-05-01T00:00:00+09:00",
                },
                {
                    "citation_id": "cit_contract_visa_conflict",
                    "title": "Imported conflict citation",
                    "source_type": "official",
                    "source": "Imported official source",
                    "ingest_at": "2026-05-01T00:00:00+09:00",
                },
                {
                    "citation_id": "cit_quota_review",
                    "title": "Imported quota citation",
                    "source_type": "official",
                    "source": "Imported official source",
                    "ingest_at": "2026-05-01T00:00:00+09:00",
                },
            ],
        },
        headers={"X-User-Role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["upserted_counts"]["companies"] == 1
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_imported", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_imported", "X-User-Role": "manager"},
    )

    assert briefing.status_code == 200
    body = briefing.json()
    assert body["company_id"] == "company_imported"
    assert body["risk_summary"]["by_risk_type"]["missing_document"] == 1
    assert "Imported Private Name" not in str(body)

    summary = client.get(
        "/api/v1/daily-briefings/sources/summary",
        headers={"X-User-Role": "admin"},
    )
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["source_counts"]["companies"] >= 1
    assert summary_body["source_counts"]["workers"] >= 1
    assert summary_body["source_counts"]["documents"] >= 1
    assert summary_body["source_counts"]["citations"] >= 1
    assert "Imported Private Name" not in str(summary_body)


def test_source_import_api_requires_admin_role() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/sources/import",
        json={"companies": []},
        headers={"X-User-Role": "manager"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "UNAUTHORIZED_ROLE"


def test_source_import_csv_api_upserts_company_worker_document_and_citation_rows() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/sources/import-csv",
        json={
            "companies_csv": (
                "company_id,company_name,timezone,quota_limit,current_foreign_worker_count\n"
                "company_csv,CSV Company,Asia/Seoul,2,1\n"
            ),
            "workers_csv": (
                "worker_id,company_id,display_name_masked,raw_name,visa_expiry_date,contract_end_date\n"
                "worker_csv_001,company_csv,[WORKER_CSV_001],CSV Private Name,2026-05-18,2026-06-30\n"
            ),
            "documents_csv": (
                "worker_id,document_type,status,required,due_date\n"
                "worker_csv_001,passport_copy,missing,true,2026-05-09\n"
            ),
            "citations_csv": (
                "citation_id,title,source_type,source,ingest_at,document_id,chunk_id,chunk_version,retrieved_at,source_url\n"
                "cit_visa_expiry,CSV visa citation,official,CSV source,2026-05-01T00:00:00+09:00,doc_visa_expiry,chunk_visa_expiry,2026-05-01,2026-05-08T00:00:00+09:00,mock://csv\n"
                "cit_missing_document,CSV document citation,official,CSV source,2026-05-01T00:00:00+09:00,doc_missing_document,chunk_missing_document,2026-05-01,2026-05-08T00:00:00+09:00,mock://csv\n"
                "cit_contract_visa_conflict,CSV conflict citation,official,CSV source,2026-05-01T00:00:00+09:00,doc_contract_visa_conflict,chunk_contract_visa_conflict,2026-05-01,2026-05-08T00:00:00+09:00,mock://csv\n"
                "cit_quota_review,CSV quota citation,official,CSV source,2026-05-01T00:00:00+09:00,doc_quota_review,chunk_quota_review,2026-05-01,2026-05-08T00:00:00+09:00,mock://csv\n"
            ),
        },
        headers={"X-User-Role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["upserted_counts"]["companies"] == 1
    assert response.json()["upserted_counts"]["workers"] == 1
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_csv", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_csv", "X-User-Role": "manager"},
    )
    assert briefing.status_code == 200
    assert briefing.json()["risk_summary"]["by_risk_type"]["missing_document"] == 1
    assert "CSV Private Name" not in str(briefing.json())


def test_briefing_history_and_metrics_summary_apis_return_pilot_operating_data() -> None:
    client = TestClient(create_app())
    first = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in first["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )
    client.post(
        f"/api/v1/approvals/{handoff_action['approval_id']}/approve",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )
    client.get(
        f"/api/v1/actions/{handoff_action['action_id']}/handoff-export.pdf",
        headers={"X-Company-Id": "company_001"},
    )
    job = client.post(
        f"/api/v1/actions/{handoff_action['action_id']}/external-delivery-jobs",
        json={"channel": "admin_scrivener", "provider": "mock_webhook"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    client.post(
        f"/api/v1/external-delivery-jobs/{job['job_id']}/dispatch",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    history = client.get(
        "/api/v1/daily-briefings/history/list?company_id=company_001",
        headers={"X-Company-Id": "company_001"},
    )
    metrics = client.get(
        "/api/v1/daily-briefings/metrics/summary?company_id=company_001",
        headers={"X-Company-Id": "company_001"},
    )

    assert history.status_code == 200
    assert history.json()["total_count"] >= 1
    assert history.json()["runs"][0]["company_id"] == "company_001"
    assert history.json()["runs"][0]["critical_count"] >= 1
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["briefing_run_count"] >= 1
    assert body["approval_rate"] >= 0
    assert body["handoff_export_count"] >= 1
    assert body["mock_dispatch_count"] >= 1
    assert "missing_evidence_count" in body


def test_source_summary_api_requires_admin_role() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/daily-briefings/sources/summary",
        headers={"X-User-Role": "manager"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "UNAUTHORIZED_ROLE"


def test_scheduler_status_api_reports_operational_configuration() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/daily-briefings/scheduler/status",
        headers={"X-User-Role": "admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["timezone"] == "Asia/Seoul"
    assert body["interval_seconds"] >= 60
    assert body["last_run"] is None


def test_citation_validation_api_returns_rag_readiness_status() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    response = client.get("/api/v1/citations/cit_visa_expiry/validation")

    assert response.status_code == 200
    body = response.json()
    assert body["citation_id"] == "cit_visa_expiry"
    assert body["validation_status"] in {
        "validated",
        "available",
        "missing_evidence",
        "stale_evidence",
        "synthetic_only",
    }
    assert "missing_evidence" in body
    assert body["stale_evidence"] is False
    assert body["synthetic_only"] is False


def test_citation_admin_list_filters_by_validation_flags() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    response = client.get(
        "/api/v1/citations/admin/list?missing_evidence=true",
        headers={"X-User-Role": "admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total_count" in body
    assert all(item["missing_evidence"] is True for item in body["items"])


def test_csv_validation_report_flags_missing_columns_bad_dates_and_orphans() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/sources/validate-csv",
        json={
            "companies_csv": "company_id,company_name\ncompany_bad,Bad Company\n",
            "workers_csv": (
                "worker_id,company_id,display_name_masked,raw_name,visa_expiry_date\n"
                "worker_bad,company_bad,[WORKER_BAD],Private Name,not-a-date\n"
            ),
            "documents_csv": (
                "worker_id,document_type,status,required,due_date\n"
                "missing_worker,passport_copy,missing,true,2026-05-09\n"
            ),
        },
        headers={"X-User-Role": "admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "invalid"
    assert body["row_counts"]["workers"] == 1
    assert any(issue["issue_type"] == "missing_required_column" for issue in body["issues"])
    assert any(issue["issue_type"] == "invalid_date" for issue in body["issues"])
    assert any(issue["issue_type"] == "unknown_worker_id" for issue in body["issues"])
    assert "Private Name" not in str(body)


def test_multipart_csv_upload_imports_selected_source_type() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/daily-briefings/sources/upload-csv",
        data={"source_type": "companies"},
        files={
            "file": (
                "companies.csv",
                "company_id,company_name,timezone,quota_limit,current_foreign_worker_count\ncompany_upload,Upload Company,Asia/Seoul,2,0\n",
                "text/csv",
            )
        },
        headers={"X-User-Role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["upserted_counts"]["companies"] == 1


def test_data_quality_summary_reports_missing_dates_orphans_and_citation_gaps() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/v1/daily-briefings/sources/import",
        json={
            "companies": [{"company_id": "company_quality", "company_name": "Quality Co"}],
            "workers": [
                {
                    "worker_id": "worker_quality_001",
                    "company_id": "company_quality",
                    "display_name_masked": "[WORKER_QUALITY_001]",
                    "raw_name": "Quality Private Name",
                    "visa_expiry_date": None,
                    "contract_end_date": None,
                }
            ],
            "documents": [
                {
                    "worker_id": "missing_worker_quality",
                    "document_type": "passport_copy",
                    "status": "missing",
                    "required": True,
                }
            ],
        },
        headers={"X-User-Role": "admin"},
    )

    response = client.get(
        "/api/v1/daily-briefings/quality/summary?company_id=company_quality",
        headers={"X-Company-Id": "company_quality"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["missing_visa_expiry_count"] == 1
    assert body["missing_contract_end_count"] == 1
    assert body["orphan_document_count"] >= 1
    assert "Quality Private Name" not in str(body)


def test_metrics_snapshot_and_scheduler_history_are_persisted() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    snapshot = client.post(
        "/api/v1/daily-briefings/metrics/snapshot",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "admin"},
    )
    scheduled = client.post(
        "/api/v1/daily-briefings/scheduled-run",
        json={"company_ids": ["company_001"], "date": "2026-05-08"},
        headers={"X-User-Role": "admin"},
    )
    history = client.get(
        "/api/v1/daily-briefings/scheduler/history?company_id=company_001",
        headers={"X-Company-Id": "company_001"},
    )

    assert snapshot.status_code == 200
    assert snapshot.json()["company_id"] == "company_001"
    assert snapshot.json()["metrics"]["briefing_run_count"] >= 1
    assert scheduled.status_code == 200
    assert history.status_code == 200
    assert history.json()["total_count"] >= 1
    assert history.json()["runs"][0]["company_ids"] == ["company_001"]


def test_citation_refresh_queue_and_pilot_feedback_log_are_persisted() -> None:
    client = TestClient(create_app())

    queued = client.post(
        "/api/v1/citations/refresh-queue",
        json={"citation_id": "cit_visa_expiry", "reason": "missing_evidence", "priority": "high"},
        headers={"X-User-Role": "admin"},
    )
    queue = client.get(
        "/api/v1/citations/refresh-queue?status=open",
        headers={"X-User-Role": "admin"},
    )
    feedback = client.post(
        "/api/v1/daily-briefings/feedback",
        json={
            "company_id": "company_001",
            "case_id": "case_manual_feedback",
            "feedback_type": "risk_incorrect",
            "message": "위험도가 높게 잡힌 이유를 다시 확인해주세요.",
        },
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager"},
    )
    feedback_list = client.get(
        "/api/v1/daily-briefings/feedback?company_id=company_001",
        headers={"X-Company-Id": "company_001"},
    )

    assert queued.status_code == 200
    assert queued.json()["status"] == "open"
    assert queue.status_code == 200
    assert queue.json()["total_count"] >= 1
    assert feedback.status_code == 200
    assert feedback.json()["feedback_type"] == "risk_incorrect"
    assert feedback_list.status_code == 200
    assert feedback_list.json()["total_count"] >= 1


def test_citation_refresh_worker_completes_manual_source_refresh_and_updates_citation() -> None:
    client = TestClient(create_app())

    queued = client.post(
        "/api/v1/citations/refresh-queue",
        json={"citation_id": "cit_visa_expiry", "reason": "stale_evidence", "priority": "high"},
        headers={"X-User-Role": "admin"},
    ).json()
    processed = client.post(
        f"/api/v1/citations/refresh-queue/{queued['queue_id']}/process",
        json={
            "refresh_mode": "manual_source",
            "citation": {
                "title": "Refreshed visa expiry official guidance",
                "source_type": "official",
                "source": "Refreshed official source text from an operator-reviewed document.",
                "ingest_at": "2026-05-08T09:00:00+09:00",
                "document_id": "doc_visa_expiry_refreshed",
                "chunk_id": "chunk_visa_expiry_refreshed",
                "chunk_version": "2026-05-08",
                "retrieved_at": "2026-05-08T09:01:00+09:00",
                "source_url": "manual://official/visa-expiry/refreshed",
            },
        },
        headers={"X-User-Role": "admin"},
    )
    refreshed = client.get("/api/v1/citations/cit_visa_expiry")
    queue = client.get(
        "/api/v1/citations/refresh-queue?status=completed",
        headers={"X-User-Role": "admin"},
    )

    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "completed"
    assert body["external_fetch_performed"] is False
    assert body["citation_id"] == "cit_visa_expiry"
    assert refreshed.status_code == 200
    assert refreshed.json()["title"] == "Refreshed visa expiry official guidance"
    assert refreshed.json()["chunk_version"] == "2026-05-08"
    assert queue.status_code == 200
    assert any(item["queue_id"] == queued["queue_id"] for item in queue.json()["items"])


def test_citation_refresh_worker_fails_safely_without_manual_source() -> None:
    client = TestClient(create_app())

    queued = client.post(
        "/api/v1/citations/refresh-queue",
        json={"citation_id": "cit_missing_document", "reason": "missing_evidence", "priority": "medium"},
        headers={"X-User-Role": "admin"},
    ).json()
    processed = client.post(
        f"/api/v1/citations/refresh-queue/{queued['queue_id']}/process",
        json={"refresh_mode": "manual_source"},
        headers={"X-User-Role": "admin"},
    )

    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "failed"
    assert body["failure_reason"] == "manual_source_required"
    assert body["external_fetch_performed"] is False


def test_official_citation_refresh_is_feature_flagged_off_by_default() -> None:
    client = TestClient(create_app())

    queued = client.post(
        "/api/v1/citations/refresh-queue",
        json={"citation_id": "cit_quota_review", "reason": "stale_evidence", "priority": "medium"},
        headers={"X-User-Role": "admin"},
    ).json()
    processed = client.post(
        f"/api/v1/citations/refresh-queue/{queued['queue_id']}/process",
        json={"refresh_mode": "official_source_fetch"},
        headers={"X-User-Role": "admin"},
    )

    assert processed.status_code == 409
    assert processed.json()["detail"]["error_code"] == "OFFICIAL_SOURCE_FETCH_DISABLED"


def test_official_citation_refresh_uses_source_url_when_feature_flag_enabled(monkeypatch, tmp_path) -> None:
    from app.api.v1 import citations
    from app.services.citation_refresh_worker import OfficialCitationRefreshWorker, OfficialSourcePayload

    class _FakeOfficialFetcher:
        def fetch(self, source_url: str) -> OfficialSourcePayload:
            return OfficialSourcePayload(
                source_url=source_url,
                status_code=200,
                content_type="text/html; charset=utf-8",
                body=(
                    b"<html><body><h1>Quota official source</h1>"
                    b"<p>Fetched official text for E-9 quota review.</p></body></html>"
                ),
            )

    monkeypatch.setattr(citations, "_official_source_fetch_enabled", lambda: True)
    monkeypatch.setattr(
        citations,
        "_build_official_source_fetch_worker",
        lambda: OfficialCitationRefreshWorker(
            fetcher=_FakeOfficialFetcher(),
            chunks_path=tmp_path / "chunks.jsonl",
            chroma_records_path=tmp_path / "chroma_records.jsonl",
            chroma_persist_dir=tmp_path / "chroma",
            chroma_collection_name="test_api_official_refresh",
        ),
    )
    client = TestClient(create_app())

    queued = client.post(
        "/api/v1/citations/refresh-queue",
        json={"citation_id": "cit_quota_review", "reason": "stale_evidence", "priority": "medium"},
        headers={"X-User-Role": "admin"},
    ).json()
    processed = client.post(
        f"/api/v1/citations/refresh-queue/{queued['queue_id']}/process",
        json={
            "refresh_mode": "official_source_fetch",
            "citation": {
                "source_url": "https://official.example.test/quota",
                "title": "Quota official source",
            },
        },
        headers={"X-User-Role": "admin"},
    )

    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "completed"
    assert body["external_fetch_performed"] is True
    refreshed = client.get("/api/v1/citations/cit_quota_review")
    assert refreshed.json()["source_url"] == "https://official.example.test/quota"
    assert refreshed.json()["chunk_version"]
    assert "Fetched official text for E-9 quota review" in refreshed.json()["source"]
    assert (tmp_path / "chunks.jsonl").exists()
    assert (tmp_path / "chroma_records.jsonl").exists()


def test_user_company_access_import_enforces_company_scope() -> None:
    client = TestClient(create_app())
    imported = client.post(
        "/api/v1/daily-briefings/sources/import",
        json={
            "companies": [
                {
                    "company_id": "company_access_only",
                    "company_name": "Access Only Company",
                    "timezone": "Asia/Seoul",
                }
            ],
            "user_company_access": [
                {
                    "user_id": "limited_manager_001",
                    "company_id": "company_access_only",
                    "role": "manager",
                }
            ],
        },
        headers={"X-User-Role": "admin"},
    )
    assert imported.status_code == 200
    assert imported.json()["upserted_counts"]["user_company_access"] == 1

    denied = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={
            "X-Company-Id": "company_001",
            "X-User-Id": "limited_manager_001",
            "X-User-Role": "manager",
        },
    )

    assert denied.status_code == 403
    assert denied.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_bearer_token_company_scope_can_replace_mock_company_header() -> None:
    client = TestClient(create_app())
    token = _bearer_token(
        {
            "sub": "token_manager_001",
            "role": "manager",
            "company_ids": ["company_001"],
        }
    )

    allowed = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"Authorization": f"Bearer {token}"},
    )
    denied = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_no_risks", "date": "2026-05-08"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["detail"]["error_code"] == "TENANT_SCOPE_VIOLATION"


def test_handoff_preview_api_returns_redacted_internal_preview() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )

    preview = client.get(f"/api/v1/actions/{handoff_action['action_id']}/handoff-preview")

    assert preview.status_code == 200
    body = preview.json()
    assert body["action_id"] == handoff_action["action_id"]
    assert "Nguyen Van A" not in str(body)
    assert body["citation_ids"]


def test_handoff_export_draft_requires_approved_action() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )
    client.post(
        f"/api/v1/approvals/{handoff_action['approval_id']}/reject",
        json={"reason": "not ready for export"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    response = client.get(
        f"/api/v1/actions/{handoff_action['action_id']}/handoff-export-draft",
        headers={"X-Company-Id": "company_001"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "APPROVAL_REQUIRED"


def test_approved_handoff_export_draft_returns_markdown_without_external_delivery() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )
    approval = client.post(
        f"/api/v1/approvals/{handoff_action['approval_id']}/approve",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )
    assert approval.status_code == 200

    response = client.get(
        f"/api/v1/actions/{handoff_action['action_id']}/handoff-export-draft",
        headers={"X-Company-Id": "company_001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "markdown"
    assert body["approval_status"] == "approved"
    assert body["external_delivery_performed"] is False
    assert body["content_markdown"].startswith("# Handoff Draft")
    assert "Nguyen" not in body["content_markdown"]
    evidence = client.get(
        f"/api/v1/cases/{handoff_action['case_id']}/evidence-events",
        headers={"X-Company-Id": "company_001"},
    ).json()
    assert any(event["event_type"] == "handoff_export_draft_generated" for event in evidence)


def test_approved_handoff_export_pdf_returns_pdf_bytes_without_external_delivery() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )
    client.post(
        f"/api/v1/approvals/{handoff_action['approval_id']}/approve",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    response = client.get(
        f"/api/v1/actions/{handoff_action['action_id']}/handoff-export.pdf",
        headers={"X-Company-Id": "company_001"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert b"Nguyen" not in response.content

    history = client.get(
        f"/api/v1/actions/{handoff_action['action_id']}/handoff-exports",
        headers={"X-Company-Id": "company_001"},
    )
    assert history.status_code == 200
    exports = history.json()
    assert exports
    assert exports[-1]["format"] == "pdf"
    assert exports[-1]["content_hash"].startswith("sha256:")
    assert exports[-1]["external_delivery_performed"] is False


def test_external_delivery_job_requires_approved_action() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )
    client.post(
        f"/api/v1/approvals/{handoff_action['approval_id']}/reject",
        json={"reason": "not ready for delivery"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    response = client.post(
        f"/api/v1/actions/{handoff_action['action_id']}/external-delivery-jobs",
        json={"channel": "admin_scrivener", "provider": "manual"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "APPROVAL_REQUIRED"


def test_approved_external_delivery_job_creates_manual_outbox_without_sending() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )
    client.post(
        f"/api/v1/approvals/{handoff_action['approval_id']}/approve",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    response = client.post(
        f"/api/v1/actions/{handoff_action['action_id']}/external-delivery-jobs",
        json={"channel": "admin_scrivener", "provider": "manual"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_manual_dispatch"
    assert body["external_send_performed"] is False
    assert body["channel"] == "admin_scrivener"
    assert body["provider"] == "manual"
    assert "Nguyen Van A" not in str(body)
    evidence = client.get(
        f"/api/v1/cases/{handoff_action['case_id']}/evidence-events",
        headers={"X-Company-Id": "company_001"},
    ).json()
    assert any(event["event_type"] == "external_delivery_job_created" for event in evidence)


def test_mock_provider_dispatch_verifies_path_without_external_send() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    handoff_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "create_handoff"
    )
    client.post(
        f"/api/v1/approvals/{handoff_action['approval_id']}/approve",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )
    job = client.post(
        f"/api/v1/actions/{handoff_action['action_id']}/external-delivery-jobs",
        json={"channel": "admin_scrivener", "provider": "mock_webhook"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()

    dispatched = client.post(
        f"/api/v1/external-delivery-jobs/{job['job_id']}/dispatch",
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    assert dispatched.status_code == 200
    body = dispatched.json()
    assert body["status"] == "mock_dispatched"
    assert body["external_send_performed"] is False
    assert body["provider_message_id"] is None
    assert "mock_provider_only" in body["warning_flags"]


def test_citation_chunk_and_source_document_apis_return_viewer_metadata() -> None:
    client = TestClient(create_app())
    _restore_canonical_visa_citation(client)
    client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    chunk = client.get("/api/v1/citations/cit_visa_expiry/chunk")
    source = client.get("/api/v1/citations/cit_visa_expiry/source-document")

    assert chunk.status_code == 200
    assert chunk.json()["chunk_id"] == "chunk_visa_expiry"
    assert chunk.json()["chunk_version"] == "2026-05-01"
    assert chunk.json()["viewer_kind"] == "chunk"
    assert source.status_code == 200
    assert source.json()["document_id"] == "doc_visa_expiry"
    assert source.json()["viewer_kind"] == "source_document"
    assert source.json()["download_available"] is False


def test_document_request_draft_api_returns_preview_only_message() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    request_action = next(
        action
        for action in briefing["recommended_actions"]
        if action["action_type"] == "request_document"
    )

    response = client.get(
        f"/api/v1/actions/{request_action['action_id']}/document-request-draft",
        headers={"X-Company-Id": "company_001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "preview_only"
    assert body["external_send_performed"] is False
    assert body["translated_text"]
    assert "Nguyen Van A" not in str(body)


def test_reject_and_revision_approval_apis_update_state() -> None:
    client = TestClient(create_app())
    briefing = client.post(
        "/api/v1/daily-briefings/run",
        json={"company_id": "company_001", "date": "2026-05-08"},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    ).json()
    first_approval_id = briefing["recommended_actions"][0]["approval_id"]
    second_approval_id = briefing["recommended_actions"][1]["approval_id"]

    rejected = client.post(
        f"/api/v1/approvals/{first_approval_id}/reject",
        json={"reason": "서류 상태를 다시 확인합니다."},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )
    revision = client.post(
        f"/api/v1/approvals/{second_approval_id}/request-revision",
        json={"reason": "질문을 추가합니다."},
        headers={"X-Company-Id": "company_001", "X-User-Role": "manager", "X-User-Id": "manager_001"},
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert revision.status_code == 200
    assert revision.json()["status"] == "revision_requested"

    refreshed = client.get(
        f"/api/v1/daily-briefings/{briefing['briefing_run_id']}",
        headers={"X-Company-Id": "company_001"},
    ).json()

    action_statuses = {
        action["approval_id"]: action["status"]
        for action in refreshed["recommended_actions"]
    }
    assert action_statuses[first_approval_id] == "rejected"
    assert action_statuses[second_approval_id] == "revision_requested"
