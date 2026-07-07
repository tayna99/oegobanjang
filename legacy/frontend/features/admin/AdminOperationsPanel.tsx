"use client";

import { useState } from "react";

import {
  createCitationRefreshQueueItem,
  createDailyBriefingMetricsSnapshot,
  getCitationAdminList,
  getCitationRefreshQueue,
  getDailyBriefingDataQualitySummary,
  getDailyBriefingHistory,
  getDailyBriefingPilotMetrics,
  getDailyBriefingSchedulerStatus,
  getDailyBriefingSourceSummary,
  getDailyBriefingSchedulerHistory,
  importDailyBriefingSourceCsv,
  processCitationRefreshQueueItem,
  uploadDailyBriefingSourceCsv,
  validateDailyBriefingSourceCsv,
} from "../../lib/api";
import type {
  CitationRefreshQueue,
  CitationAdminList,
  DailyBriefingCsvValidationReport,
  DailyBriefingDataQualitySummary,
  DailyBriefingHistory,
  DailyBriefingImportResult,
  DailyBriefingMetricsSnapshot,
  DailyBriefingPilotMetrics,
  DailyBriefingSchedulerHistory,
  DailyBriefingSourceSummary,
  ScheduledDailyBriefingStatus,
} from "../../types/dailyBriefing";

const sampleCompaniesCsv =
  "company_id,company_name,timezone,quota_limit,current_foreign_worker_count\ncompany_admin_csv,Admin CSV Company,Asia/Seoul,2,1\n";
const sampleWorkersCsv =
  "worker_id,company_id,display_name_masked,raw_name,visa_expiry_date,contract_end_date\nworker_admin_csv_001,company_admin_csv,[WORKER_ADMIN_CSV_001],Admin Private Name,2026-05-18,2026-06-30\n";
const sampleDocumentsCsv =
  "worker_id,document_type,status,required,due_date\nworker_admin_csv_001,passport_copy,missing,true,2026-05-09\n";
const sampleCitationsCsv =
  "citation_id,title,source_type,source,ingest_at,document_id,chunk_id,chunk_version,retrieved_at,source_url\ncit_visa_expiry,Admin visa citation,official,Admin source,2026-05-01T00:00:00+09:00,doc_visa_expiry,chunk_visa_expiry,2026-05-01,2026-05-08T00:00:00+09:00,mock://admin\ncit_missing_document,Admin document citation,official,Admin source,2026-05-01T00:00:00+09:00,doc_missing_document,chunk_missing_document,2026-05-01,2026-05-08T00:00:00+09:00,mock://admin\n";
const sampleCandidatesCsv =
  "candidate_id,company_id,display_name_masked,raw_name,status\ncandidate_admin_001,company_admin_csv,[CANDIDATE_ADMIN_001],Candidate Private Name,registered\n";
const sampleCandidateDocumentsCsv =
  "candidate_id,document_type,status,required,due_date\ncandidate_admin_001,passport_copy,missing,true,2026-05-20\n";
const sampleReportingEventsCsv =
  "event_id,company_id,worker_id,event_type,occurred_at,discovered_at,reporting_due_date,reported_at,status\nreport_admin_001,company_admin_csv,worker_admin_csv_001,employment_change,2026-05-01,2026-05-02,2026-05-10,,open\n";
const sampleUserCompanyAccessCsv =
  "user_id,company_id,role\nmanager_admin_csv,company_admin_csv,manager\n";

export function AdminOperationsPanel() {
  const [companyId, setCompanyId] = useState("company_001");
  const [companiesCsv, setCompaniesCsv] = useState(sampleCompaniesCsv);
  const [workersCsv, setWorkersCsv] = useState(sampleWorkersCsv);
  const [documentsCsv, setDocumentsCsv] = useState(sampleDocumentsCsv);
  const [citationsCsv, setCitationsCsv] = useState(sampleCitationsCsv);
  const [candidatesCsv, setCandidatesCsv] = useState(sampleCandidatesCsv);
  const [candidateDocumentsCsv, setCandidateDocumentsCsv] = useState(sampleCandidateDocumentsCsv);
  const [reportingEventsCsv, setReportingEventsCsv] = useState(sampleReportingEventsCsv);
  const [userCompanyAccessCsv, setUserCompanyAccessCsv] = useState(sampleUserCompanyAccessCsv);
  const [showMissingEvidence, setShowMissingEvidence] = useState(true);
  const [showStaleEvidence, setShowStaleEvidence] = useState(false);
  const [showSyntheticOnly, setShowSyntheticOnly] = useState(false);
  const [sourceSummary, setSourceSummary] = useState<DailyBriefingSourceSummary | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<ScheduledDailyBriefingStatus | null>(null);
  const [history, setHistory] = useState<DailyBriefingHistory | null>(null);
  const [metrics, setMetrics] = useState<DailyBriefingPilotMetrics | null>(null);
  const [quality, setQuality] = useState<DailyBriefingDataQualitySummary | null>(null);
  const [schedulerHistory, setSchedulerHistory] = useState<DailyBriefingSchedulerHistory | null>(null);
  const [metricsSnapshot, setMetricsSnapshot] = useState<DailyBriefingMetricsSnapshot | null>(null);
  const [citations, setCitations] = useState<CitationAdminList | null>(null);
  const [refreshQueue, setRefreshQueue] = useState<CitationRefreshQueue | null>(null);
  const [validationReport, setValidationReport] = useState<DailyBriefingCsvValidationReport | null>(null);
  const [importResult, setImportResult] = useState<DailyBriefingImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshAdminState() {
    setError(null);
    try {
      const [
        summary,
        scheduler,
        runHistory,
        pilotMetrics,
        qualitySummary,
        schedulerRuns,
        citationList,
        queuedCitations,
      ] = await Promise.all([
        getDailyBriefingSourceSummary(),
        getDailyBriefingSchedulerStatus(),
        getDailyBriefingHistory(companyId),
        getDailyBriefingPilotMetrics(companyId),
        getDailyBriefingDataQualitySummary(companyId),
        getDailyBriefingSchedulerHistory(companyId),
        getCitationAdminList({
          missingEvidence: showMissingEvidence ? true : undefined,
          staleEvidence: showStaleEvidence ? true : undefined,
          syntheticOnly: showSyntheticOnly ? true : undefined,
        }),
        getCitationRefreshQueue(),
      ]);
      setSourceSummary(summary);
      setSchedulerStatus(scheduler);
      setHistory(runHistory);
      setMetrics(pilotMetrics);
      setQuality(qualitySummary);
      setSchedulerHistory(schedulerRuns);
      setCitations(citationList);
      setRefreshQueue(queuedCitations);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Admin refresh failed");
    }
  }

  function csvPayload() {
    return {
      companies_csv: companiesCsv,
      workers_csv: workersCsv,
      documents_csv: documentsCsv,
      citations_csv: citationsCsv,
      candidates_csv: candidatesCsv,
      candidate_documents_csv: candidateDocumentsCsv,
      reporting_events_csv: reportingEventsCsv,
      user_company_access_csv: userCompanyAccessCsv,
    };
  }

  async function handleCsvValidation() {
    setError(null);
    try {
      const report = await validateDailyBriefingSourceCsv(csvPayload());
      setValidationReport(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV validation failed");
    }
  }

  async function handleCsvImport() {
    setError(null);
    try {
      const result = await importDailyBriefingSourceCsv(csvPayload());
      setImportResult(result);
      await refreshAdminState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV import failed");
    }
  }

  async function handleMultipartUpload(file: File | null) {
    if (!file) {
      return;
    }
    setError(null);
    try {
      const result = await uploadDailyBriefingSourceCsv("companies", file);
      setImportResult(result);
      await refreshAdminState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV upload failed");
    }
  }

  async function handleMetricsSnapshot() {
    setError(null);
    try {
      const snapshot = await createDailyBriefingMetricsSnapshot(companyId);
      setMetricsSnapshot(snapshot);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Metrics snapshot failed");
    }
  }

  async function handleQueueCitationRefresh(citationId: string) {
    setError(null);
    try {
      await createCitationRefreshQueueItem(citationId, "admin_review_requested", "medium");
      setRefreshQueue(await getCitationRefreshQueue());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Citation refresh queue failed");
    }
  }

  async function handleProcessCitationRefresh(queueId: string, citationId: string) {
    setError(null);
    try {
      await processCitationRefreshQueueItem(queueId, citationId);
      setRefreshQueue(await getCitationRefreshQueue());
      await refreshAdminState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Citation refresh processing failed");
    }
  }

  return (
    <section className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
          Daily Briefing Admin
        </p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950">
          Pilot operations, source data, metrics, and citation readiness.
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">
          This admin view is for MVP pilot operations. It does not send messages or handoff
          packages externally.
        </p>
        <div className="mt-6 flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-2 text-sm font-bold text-slate-700">
            Company ID
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-slate-950"
              onChange={(event) => setCompanyId(event.target.value)}
              value={companyId}
            />
          </label>
          <button
            className="rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white"
            onClick={refreshAdminState}
          >
            Refresh admin state
          </button>
        </div>
        {error ? <p className="mt-4 text-sm font-bold text-red-700">{error}</p> : null}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <AdminMetric label="Source companies" value={sourceSummary?.source_counts.companies ?? 0} />
        <AdminMetric label="Scheduler enabled" value={schedulerStatus?.enabled ? 1 : 0} />
        <AdminMetric label="Briefing runs" value={history?.total_count ?? 0} />
        <AdminMetric label="Missing evidence" value={metrics?.missing_evidence_count ?? 0} />
      </div>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-black text-slate-950">Data quality control</h2>
        <p className="mt-2 text-sm text-slate-600">
          Quality checks stay internal: no external source refresh, no legal conclusion, no worker scoring.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <AdminMetric label="Missing visa dates" value={quality?.missing_visa_expiry_count ?? 0} />
          <AdminMetric label="Missing contracts" value={quality?.missing_contract_end_count ?? 0} />
          <AdminMetric label="Orphan docs" value={quality?.orphan_document_count ?? 0} />
          <AdminMetric label="Citation gaps" value={quality?.citation_gap_count ?? 0} />
        </div>
        {quality?.issues.length ? (
          <div className="mt-4 grid gap-2">
            {quality.issues.map((issue) => (
              <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm" key={issue.issue_type}>
                <span className="font-black text-slate-950">{issue.issue_type}</span>
                <span className="ml-3 text-slate-600">{issue.severity} / {issue.count}</span>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-black text-slate-950">CSV source import</h2>
          <p className="mt-2 text-sm text-slate-600">
            CSV input is admin-only. Raw names are stored for lookup but never returned in summaries.
          </p>
          <label className="mt-5 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
            Companies CSV
            <textarea
              className="mt-2 min-h-28 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
              onChange={(event) => setCompaniesCsv(event.target.value)}
              value={companiesCsv}
            />
          </label>
          <label className="mt-4 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
            Workers CSV
            <textarea
              className="mt-2 min-h-28 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
              onChange={(event) => setWorkersCsv(event.target.value)}
              value={workersCsv}
            />
          </label>
          <label className="mt-4 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
            Documents CSV
            <textarea
              className="mt-2 min-h-28 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
              onChange={(event) => setDocumentsCsv(event.target.value)}
              value={documentsCsv}
            />
          </label>
          <label className="mt-4 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
            Citations CSV
            <textarea
              className="mt-2 min-h-28 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
              onChange={(event) => setCitationsCsv(event.target.value)}
              value={citationsCsv}
            />
          </label>
          <details className="mt-4 rounded-2xl border border-slate-200 p-4">
            <summary className="cursor-pointer text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
              Optional pilot CSV sources
            </summary>
            <label className="mt-4 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
              Candidates CSV
              <textarea
                className="mt-2 min-h-24 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
                onChange={(event) => setCandidatesCsv(event.target.value)}
                value={candidatesCsv}
              />
            </label>
            <label className="mt-4 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
              Candidate Documents CSV
              <textarea
                className="mt-2 min-h-24 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
                onChange={(event) => setCandidateDocumentsCsv(event.target.value)}
                value={candidateDocumentsCsv}
              />
            </label>
            <label className="mt-4 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
              Reporting Events CSV
              <textarea
                className="mt-2 min-h-24 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
                onChange={(event) => setReportingEventsCsv(event.target.value)}
                value={reportingEventsCsv}
              />
            </label>
            <label className="mt-4 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
              User Company Access CSV
              <textarea
                className="mt-2 min-h-24 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs"
                onChange={(event) => setUserCompanyAccessCsv(event.target.value)}
                value={userCompanyAccessCsv}
              />
            </label>
          </details>
          <button
            className="mt-4 rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white"
            onClick={handleCsvValidation}
          >
            Validate CSV source rows
          </button>
          <button
            className="ml-3 mt-4 rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white"
            onClick={handleCsvImport}
          >
            Import CSV source rows
          </button>
          <label className="ml-3 inline-flex cursor-pointer rounded-full border border-slate-300 px-5 py-3 text-sm font-bold text-slate-700">
            Upload companies.csv
            <input
              accept=".csv,text/csv"
              className="hidden"
              onChange={(event) => handleMultipartUpload(event.target.files?.[0] ?? null)}
              type="file"
            />
          </label>
          {validationReport ? (
            <pre className="mt-4 overflow-auto rounded-2xl bg-amber-50 p-4 text-xs">
              {JSON.stringify(validationReport, null, 2)}
            </pre>
          ) : null}
          {importResult ? (
            <pre className="mt-4 overflow-auto rounded-2xl bg-slate-50 p-4 text-xs">
              {JSON.stringify(importResult.upserted_counts, null, 2)}
            </pre>
          ) : null}
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-black text-slate-950">Pilot metrics</h2>
          <p className="mt-2 text-sm text-slate-600">
            MVP metrics are calculated live and can be snapshotted for pilot reporting.
          </p>
          <button
            className="mt-4 rounded-full border border-slate-300 px-4 py-2 text-sm font-black text-slate-700"
            onClick={handleMetricsSnapshot}
          >
            Save metrics snapshot
          </button>
          <div className="mt-5 grid gap-3">
            <AdminRow label="Approval rate" value={formatRate(metrics?.approval_rate)} />
            <AdminRow label="Revision rate" value={formatRate(metrics?.revision_rate)} />
            <AdminRow label="Handoff exports" value={metrics?.handoff_export_count ?? 0} />
            <AdminRow label="Mock dispatches" value={metrics?.mock_dispatch_count ?? 0} />
            <AdminRow label="HIGH/CRITICAL risks" value={metrics?.high_or_critical_risk_count ?? 0} />
          </div>
          {metricsSnapshot ? (
            <pre className="mt-4 overflow-auto rounded-2xl bg-slate-50 p-4 text-xs">
              {JSON.stringify(metricsSnapshot, null, 2)}
            </pre>
          ) : null}
        </section>
      </div>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-black text-slate-950">Recent briefing runs</h2>
        <div className="mt-4 grid gap-3">
          {(history?.runs ?? []).map((run) => (
            <div className="rounded-2xl bg-slate-50 p-4 text-sm" key={run.briefing_run_id}>
              <p className="font-black text-slate-950">{run.date} / {run.company_id}</p>
              <p>Critical {run.critical_count}, High {run.high_count}, Pending {run.approval_pending_count}</p>
              <p className="text-xs text-slate-500">Snapshot: {run.source_snapshot_hash}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-black text-slate-950">Scheduler run history</h2>
        <div className="mt-4 grid gap-3">
          {(schedulerHistory?.runs ?? []).map((run) => (
            <div className="rounded-2xl bg-slate-50 p-4 text-sm" key={run.run_id}>
              <p className="font-black text-slate-950">{run.date} / {run.status}</p>
              <p>Companies {run.total_companies}, succeeded {run.succeeded_count}, failed {run.failed_count}</p>
              <p className="text-xs text-slate-500">{run.company_ids.join(", ")}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-black text-slate-950">Citation readiness</h2>
        <p className="mt-2 text-sm text-slate-600">
          Filter citations by readiness flags so the pilot team can refresh official sources.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <label className="rounded-full bg-amber-50 px-4 py-2 text-sm font-bold text-amber-950">
            <input
              checked={showMissingEvidence}
              className="mr-2"
              onChange={(event) => setShowMissingEvidence(event.target.checked)}
              type="checkbox"
            />
            Missing evidence
          </label>
          <label className="rounded-full bg-orange-50 px-4 py-2 text-sm font-bold text-orange-950">
            <input
              checked={showStaleEvidence}
              className="mr-2"
              onChange={(event) => setShowStaleEvidence(event.target.checked)}
              type="checkbox"
            />
            Stale evidence
          </label>
          <label className="rounded-full bg-red-50 px-4 py-2 text-sm font-bold text-red-950">
            <input
              checked={showSyntheticOnly}
              className="mr-2"
              onChange={(event) => setShowSyntheticOnly(event.target.checked)}
              type="checkbox"
            />
            Synthetic only
          </label>
          <button
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-black text-slate-700"
            onClick={refreshAdminState}
          >
            Apply citation filters
          </button>
        </div>
        <div className="mt-4 grid gap-3">
          {(citations?.items ?? []).map((citation) => (
            <div className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-950" key={citation.citation_id}>
              <p className="font-black">{citation.title}</p>
              <p>Status: {citation.validation_status}</p>
              <p>Policy update needed: {String(citation.policy_update_needed)}</p>
              <button
                className="mt-3 rounded-full bg-amber-950 px-4 py-2 text-xs font-black text-white"
                onClick={() => handleQueueCitationRefresh(citation.citation_id)}
              >
                Queue refresh review
              </button>
            </div>
          ))}
        </div>
        {refreshQueue ? (
          <div className="mt-4 grid gap-3">
            {refreshQueue.items.slice(0, 5).map((item) => (
              <div className="rounded-2xl bg-slate-50 p-4 text-sm" key={item.queue_id}>
                <p className="font-black text-slate-950">{item.citation_id}</p>
                <p>Status: {item.status} / Reason: {item.reason}</p>
                <p className="text-xs text-slate-500">
                  External fetch performed: {String(item.external_fetch_performed)}
                </p>
                {item.status === "open" ? (
                  <button
                    className="mt-3 rounded-full bg-slate-950 px-4 py-2 text-xs font-black text-white"
                    onClick={() => handleProcessCitationRefresh(item.queue_id, item.citation_id)}
                  >
                    Process manual refresh
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </section>
  );
}

function AdminMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">{label}</p>
      <p className="mt-2 text-4xl font-black text-slate-950">{value}</p>
    </div>
  );
}

function AdminRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between rounded-2xl bg-slate-50 px-4 py-3 text-sm">
      <span className="font-bold text-slate-600">{label}</span>
      <span className="font-black text-slate-950">{value}</span>
    </div>
  );
}

function formatRate(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}
