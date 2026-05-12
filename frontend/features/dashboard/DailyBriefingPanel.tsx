"use client";

import { useState } from "react";

import {
  approveAction,
  createExternalDeliveryJob,
  dispatchExternalDeliveryJob,
  downloadHandoffExportPdf,
  getCitationChunk,
  getCitationSourceDocument,
  getCitationValidation,
  getDocumentRequestDraft,
  getHandoffExportArtifacts,
  getHandoffPreview,
  rejectAction,
  requestRevision,
  runDailyBriefing,
} from "../../lib/api";
import type {
  DailyBriefingResult,
  CitationChunkView,
  CitationSourceDocumentView,
  CitationValidationStatus,
  DocumentRequestDraft,
  ExternalDeliveryJob,
  HandoffExportArtifact,
  HandoffPreview,
  NextAction,
} from "../../types/dailyBriefing";
import { DailyBriefingChatPanel } from "./DailyBriefingChatPanel";

const severityTone = {
  CRITICAL: "border-red-500 bg-red-50 text-red-900",
  HIGH: "border-orange-500 bg-orange-50 text-orange-900",
  MEDIUM: "border-amber-400 bg-amber-50 text-amber-900",
  LOW: "border-slate-300 bg-slate-50 text-slate-800",
};

const riskTypeLabel = {
  contract_visa_conflict: "Contract / visa conflict",
  candidate_readiness: "Candidate document readiness",
  missing_document: "Missing document",
  quota_review: "Quota review",
  reporting_deadline: "Reporting deadline",
  visa_expiry: "Visa expiry",
};

export function DailyBriefingPanel() {
  const [companyId, setCompanyId] = useState("company_001");
  const [date, setDate] = useState("2026-05-08");
  const [briefing, setBriefing] = useState<DailyBriefingResult | null>(null);
  const [preview, setPreview] = useState<HandoffPreview | null>(null);
  const [documentDraft, setDocumentDraft] = useState<DocumentRequestDraft | null>(null);
  const [deliveryJob, setDeliveryJob] = useState<ExternalDeliveryJob | null>(null);
  const [exportArtifacts, setExportArtifacts] = useState<HandoffExportArtifact[]>([]);
  const [citationChunk, setCitationChunk] = useState<CitationChunkView | null>(null);
  const [citationSource, setCitationSource] = useState<CitationSourceDocumentView | null>(null);
  const [citationValidation, setCitationValidation] = useState<CitationValidationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshBriefing() {
    return runDailyBriefing(companyId, date);
  }

  async function handleRunBriefing() {
    setLoading(true);
    setError(null);
    try {
      setBriefing(await refreshBriefing());
      setPreview(null);
      setDocumentDraft(null);
      setDeliveryJob(null);
      setExportArtifacts([]);
      setCitationChunk(null);
      setCitationSource(null);
      setCitationValidation(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Daily briefing failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(action: NextAction) {
    setError(null);
    try {
      await approveAction(action.approval_id, companyId);
      setBriefing(await refreshBriefing());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    }
  }

  async function handleReject(action: NextAction) {
    setError(null);
    try {
      await rejectAction(action.approval_id, "Rejected during internal review.", companyId);
      setBriefing(await refreshBriefing());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    }
  }

  async function handleRevision(action: NextAction) {
    setError(null);
    try {
      await requestRevision(action.approval_id, "Please revise this draft.", companyId);
      setBriefing(await refreshBriefing());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revision request failed");
    }
  }

  async function handleOpenPreview(action: NextAction) {
    setError(null);
    try {
      setPreview(await getHandoffPreview(action.action_id, companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Handoff preview failed");
    }
  }

  async function handleOpenDocumentDraft(action: NextAction) {
    setError(null);
    try {
      setDocumentDraft(await getDocumentRequestDraft(action.action_id, companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document request draft failed");
    }
  }

  async function handleCreateDeliveryJob(action: NextAction) {
    setError(null);
    try {
      setDeliveryJob(await createExternalDeliveryJob(action.action_id, companyId, "mock_webhook"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "External delivery job failed");
    }
  }

  async function handleMockDispatch() {
    if (!deliveryJob) {
      return;
    }
    setError(null);
    try {
      setDeliveryJob(await dispatchExternalDeliveryJob(deliveryJob.job_id, companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mock dispatch verification failed");
    }
  }

  async function handleDownloadExport(action: NextAction) {
    setError(null);
    try {
      const pdf = await downloadHandoffExportPdf(action.action_id, companyId);
      const url = window.URL.createObjectURL(pdf);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${action.action_id}-handoff-export.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
      setExportArtifacts(await getHandoffExportArtifacts(action.action_id, companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "PDF export draft failed");
    }
  }

  async function handleOpenCitation(citationId: string) {
    setError(null);
    try {
      const [chunk, source, validation] = await Promise.all([
        getCitationChunk(citationId),
        getCitationSourceDocument(citationId),
        getCitationValidation(citationId),
      ]);
      setCitationChunk(chunk);
      setCitationSource(source);
      setCitationValidation(validation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Citation viewer failed");
    }
  }

  return (
    <section className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
          E-9 operations risk MVP
        </p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950">
          Daily Briefing: deadlines, documents, approvals, and evidence.
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
          The system prepares approval-ready drafts only. It does not send messages,
          submit government forms, or deliver handoff packages externally.
        </p>
        <p className="mt-3 max-w-3xl rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
          MVP safety mode: approvals create internal records only. Mock dispatch verifies the
          delivery boundary and audit trail, but no Kakao, email, or admin-office transfer is performed.
        </p>
        <div className="mt-6 grid gap-3 md:grid-cols-[1fr_180px_auto]">
          <label className="flex flex-col gap-2 text-sm font-bold text-slate-700">
            Company ID
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-slate-950"
              onChange={(event) => setCompanyId(event.target.value)}
              value={companyId}
            />
          </label>
          <label className="flex flex-col gap-2 text-sm font-bold text-slate-700">
            Date
            <input
              className="rounded-2xl border border-slate-200 px-4 py-3 text-slate-950"
              onChange={(event) => setDate(event.target.value)}
              type="date"
              value={date}
            />
          </label>
          <button
            className="self-end rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white shadow-sm disabled:opacity-50"
            disabled={loading}
            onClick={handleRunBriefing}
          >
            {loading ? "Generating..." : "Generate briefing"}
          </button>
        </div>
        {error ? <p className="mt-4 text-sm font-semibold text-red-700">{error}</p> : null}
      </div>

      <DailyBriefingChatPanel companyId={companyId} />

      {briefing ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="CRITICAL" value={briefing.risk_summary.critical_count} />
            <Metric label="HIGH" value={briefing.risk_summary.high_count} />
            <Metric label="MEDIUM" value={briefing.risk_summary.medium_count} />
            <Metric label="TOTAL" value={briefing.risk_summary.total_count} />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Metric
              label="APPROVAL PENDING"
              value={briefing.recommended_actions.filter((action) => action.status === "pending_approval").length}
            />
            <Metric
              label="MISSING EVIDENCE"
              value={briefing.citation_summaries.filter((citation) => citation.missing_evidence).length}
            />
            <Metric
              label="READY ACTIONS"
              value={briefing.recommended_actions.filter((action) => action.status === "approved").length}
            />
          </div>

          {briefing.items.length === 0 ? (
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-6 text-emerald-900">
              No approval-ready risk items were found for this date.
            </div>
          ) : null}

          <div className="grid gap-4">
            {briefing.items.map((item) => {
              const actions = briefing.recommended_actions.filter((action) =>
                item.next_action_ids.includes(action.action_id),
              );
              return (
                <article
                  className={`rounded-3xl border p-6 ${severityTone[item.severity]}`}
                  key={item.item_id}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.25em]">
                        {item.severity} / {riskTypeLabel[item.risk_type] ?? item.risk_type}
                      </p>
                      <h2 className="mt-2 text-2xl font-black">{item.subject_id}</h2>
                      <p className="mt-2 text-sm">
                        {item.expired
                          ? `Overdue D+${item.days_overdue}`
                          : item.d_day !== null
                            ? `D-${item.d_day}`
                            : "No D-day"}
                      </p>
                    </div>
                    <a
                      className="rounded-full border border-current px-4 py-2 text-xs font-bold"
                      href={`/evidence?case_id=${item.case_id}&company_id=${briefing.company_id}`}
                    >
                      Evidence Log
                    </a>
                  </div>
                  {item.missing_documents.length ? (
                    <p className="mt-4 text-sm font-semibold">
                      Missing documents: {item.missing_documents.join(", ")}
                    </p>
                  ) : null}
                  <div className="mt-4 flex flex-wrap gap-2">
                    {item.citation_ids.map((citationId) => {
                      const citation = briefing.citation_summaries.find(
                        (summary) => summary.citation_id === citationId,
                      );
                      return (
                        <button
                          className="rounded-full bg-white/70 px-3 py-1 text-left text-xs font-semibold"
                          key={citationId}
                          onClick={() => handleOpenCitation(citationId)}
                        >
                          Evidence: {citation?.title ?? citationId}
                          {citation?.chunk_version ? ` (${citation.chunk_version})` : ""}
                        </button>
                      );
                    })}
                  </div>
                  <div className="mt-5 flex flex-wrap gap-3">
                    {actions.map((action) => (
                      <span className="flex flex-wrap gap-2" key={action.action_id}>
                        {action.action_type === "create_handoff" ? (
                          <>
                            <button
                              className="rounded-full border border-white/70 px-4 py-2 text-xs font-black"
                              onClick={() => handleOpenPreview(action)}
                            >
                              Handoff preview
                            </button>
                            <button
                              className="rounded-full border border-white/70 px-4 py-2 text-xs font-black"
                              onClick={() => handleDownloadExport(action)}
                            >
                              PDF export draft
                            </button>
                            <button
                              className="rounded-full border border-white/70 px-4 py-2 text-xs font-black"
                              onClick={() => handleCreateDeliveryJob(action)}
                            >
                              Create mock outbox record
                            </button>
                          </>
                        ) : null}
                        {action.action_type === "request_document" ? (
                          <button
                            className="rounded-full border border-white/70 px-4 py-2 text-xs font-black"
                            onClick={() => handleOpenDocumentDraft(action)}
                          >
                            Document request draft
                          </button>
                        ) : null}
                        <button
                          className="rounded-full bg-white px-4 py-2 text-xs font-black text-slate-950 shadow-sm disabled:opacity-60"
                          disabled={action.status !== "pending_approval"}
                          onClick={() => handleApprove(action)}
                        >
                          {action.status === "approved" ? "Approved" : `Approve ${action.label}`}
                        </button>
                        <button
                          className="rounded-full bg-white/70 px-4 py-2 text-xs font-black text-slate-950 disabled:opacity-60"
                          disabled={action.status !== "pending_approval"}
                          onClick={() => handleRevision(action)}
                        >
                          Request revision
                        </button>
                        <button
                          className="rounded-full bg-red-900 px-4 py-2 text-xs font-black text-white disabled:opacity-60"
                          disabled={action.status !== "pending_approval"}
                          onClick={() => handleReject(action)}
                        >
                          Reject
                        </button>
                      </span>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
          {preview ? (
            <aside className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-400">
                    Internal Handoff Preview
                  </p>
                  <h2 className="mt-2 text-2xl font-black">Review-only handoff package</h2>
                </div>
                <button className="text-sm font-bold text-slate-300" onClick={() => setPreview(null)}>
                  Close
                </button>
              </div>
              <pre className="mt-5 overflow-auto rounded-2xl bg-white/10 p-4 text-xs leading-6 text-slate-100">
                {JSON.stringify(preview.content_redacted, null, 2)}
              </pre>
              <p className="mt-4 text-xs text-slate-300">
                Preview only. No package was sent to an external party.
              </p>
            </aside>
          ) : null}
          {documentDraft ? (
            <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
                    Preview-only Document Request
                  </p>
                  <h2 className="mt-2 text-2xl font-black text-slate-950">Document request message draft</h2>
                </div>
                <button className="text-sm font-bold text-slate-500" onClick={() => setDocumentDraft(null)}>
                  Close
                </button>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Korean</p>
                  <p className="mt-3 text-sm leading-6 text-slate-800">{documentDraft.korean_text}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
                    Draft translation
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-800">{documentDraft.translated_text}</p>
                </div>
              </div>
              <p className="mt-4 text-xs font-semibold text-slate-500">
                External send performed: {String(documentDraft.external_send_performed)}
              </p>
            </aside>
          ) : null}
          {deliveryJob ? (
            <aside className="rounded-3xl border border-blue-200 bg-blue-50 p-6 text-blue-950 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.25em] text-blue-700">
                    MVP dispatch boundary
                  </p>
                  <h2 className="mt-2 text-2xl font-black">No external transfer was performed</h2>
                </div>
                <button className="text-sm font-bold text-blue-700" onClick={() => setDeliveryJob(null)}>
                  Close
                </button>
              </div>
              <p className="mt-4 text-sm">
                Status: {deliveryJob.status}. Provider: {deliveryJob.provider}. External send performed:{" "}
                {String(deliveryJob.external_send_performed)}. This record is for internal audit and
                dispatch-path verification only.
              </p>
              {deliveryJob.status === "pending_manual_dispatch" ? (
                <button
                  className="mt-5 rounded-full bg-blue-950 px-4 py-2 text-xs font-black text-white"
                  onClick={handleMockDispatch}
                >
                  Verify mock dispatch path
                </button>
              ) : null}
            </aside>
          ) : null}
          {exportArtifacts.length ? (
            <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
                Export artifact history
              </p>
              <div className="mt-4 grid gap-3">
                {exportArtifacts.map((artifact) => (
                  <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700" key={artifact.artifact_id}>
                    <p className="font-black text-slate-950">{artifact.format.toUpperCase()} draft</p>
                    <p className="mt-1">Hash: {artifact.content_hash}</p>
                    <p>External delivery performed: {String(artifact.external_delivery_performed)}</p>
                    <p className="text-xs text-slate-500">Created: {artifact.created_at}</p>
                  </div>
                ))}
              </div>
            </aside>
          ) : null}
          {citationChunk && citationSource && citationValidation ? (
            <aside className="rounded-3xl border border-indigo-200 bg-indigo-50 p-6 text-indigo-950 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.25em] text-indigo-700">
                    Citation source viewer
                  </p>
                  <h2 className="mt-2 text-2xl font-black">{citationSource.title}</h2>
                </div>
                <button
                  className="text-sm font-bold text-indigo-700"
                  onClick={() => {
                    setCitationChunk(null);
                    setCitationSource(null);
                    setCitationValidation(null);
                  }}
                >
                  Close
                </button>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-[1fr_1.4fr]">
                <div className="rounded-2xl bg-white/70 p-4 text-sm">
                  <p className="font-black">Source metadata</p>
                  <p className="mt-2">Citation: {citationSource.citation_id}</p>
                  <p>Document: {citationSource.document_id ?? "not linked"}</p>
                  <p>Source type: {citationSource.source_type}</p>
                  <p>Retrieved: {citationSource.retrieved_at ?? "not recorded"}</p>
                  <p>Chunk version: {citationChunk.chunk_version ?? "not versioned"}</p>
                  <p>Validation: {citationValidation.validation_status}</p>
                  <p>Missing evidence: {String(citationValidation.missing_evidence)}</p>
                  <p>Policy update needed: {String(citationValidation.policy_update_needed)}</p>
                  <p>Original PDF available: {String(citationSource.original_pdf_available)}</p>
                </div>
                <div className="rounded-2xl bg-white p-4 text-sm leading-6">
                  <p className="mb-3 font-black">Retrieved chunk</p>
                  <p>{citationChunk.chunk_text}</p>
                </div>
              </div>
              <p className="mt-4 text-xs font-semibold text-indigo-700">
                This viewer shows the retrieved evidence metadata used by the risk briefing. It does not make a legal conclusion.
              </p>
            </aside>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">{label}</p>
      <p className="mt-2 text-4xl font-black text-slate-950">{value}</p>
    </div>
  );
}
