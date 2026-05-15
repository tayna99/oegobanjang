import type {
  ApprovalActionResult,
  DailyBriefingResult,
  AgentChatResponse,
  CaseAuditReview,
  CitationChunkView,
  CitationDetail,
  CitationSourceDocumentView,
  CitationValidationStatus,
  CitationAdminList,
  DailyBriefingCsvImportPayload,
  DailyBriefingCsvValidationReport,
  DailyBriefingDataQualitySummary,
  DailyBriefingHistory,
  DailyBriefingImportResult,
  DailyBriefingMetricsSnapshot,
  DailyBriefingPilotMetrics,
  DailyBriefingSchedulerHistory,
  DailyBriefingSourceSummary,
  DocumentRequestDraft,
  EvidenceEvent,
  ExternalDeliveryJob,
  HandoffExportArtifact,
  HandoffExportDraft,
  HandoffPreview,
  CitationRefreshQueue,
  ScheduledDailyBriefingStatus,
} from "../types/dailyBriefing";
import { getOperatorHeaders } from "./operatorContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

function companyHeaders(companyId: string, overrides: Parameters<typeof getOperatorHeaders>[0] = {}) {
  return getOperatorHeaders({ companyId, ...overrides });
}

function adminHeaders(overrides: Parameters<typeof getOperatorHeaders>[0] = {}) {
  return getOperatorHeaders({ role: "admin", ...overrides });
}

export type ApiResult<T> = {
  ok: boolean;
  data?: T;
  error?: string;
};

export async function safeJsonFetch<T>(url: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(url, {
      headers: {
        accept: "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return { ok: false, error: `HTTP ${response.status}` };
    }

    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "unknown error",
    };
  }
}

export async function fetchCompanyList(): Promise<{ id: string; name: string }[]> {
  const response = await fetch(`${API_BASE_URL}/proto/companies`, {
    headers: { accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) return [];
  return response.json();
}

export async function runDailyBriefing(
  companyId: string,
  date = new Date().toISOString().slice(0, 10),
): Promise<DailyBriefingResult> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...companyHeaders(companyId),
    },
    body: JSON.stringify({ company_id: companyId, date }),
  });

  if (!response.ok) {
    throw new Error(`Daily briefing failed with ${response.status}`);
  }

  return response.json();
}

export async function sendAgentChatMessage({
  message,
  companyId = "",
  workspaceId,
  activeTab = "today",
  date,
  selectedCaseId,
  selectedActionId,
  sessionId,
}: {
  message: string;
  companyId?: string;
  workspaceId?: string;
  activeTab?: string;
  date?: string;
  selectedCaseId?: string;
  selectedActionId?: string;
  sessionId?: string;
}): Promise<AgentChatResponse> {
  const response = await fetch(`${API_BASE_URL}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...companyHeaders(companyId),
    },
    body: JSON.stringify({
      message,
      companyId,
      workspaceId,
      activeTab,
      date,
      selectedCaseId,
      selectedActionId,
      sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Agent chat failed with ${response.status}`);
  }

  return response.json();
}

export async function approveAction(
  approvalId: string,
  companyId = "",
): Promise<ApprovalActionResult> {
  const response = await fetch(`${API_BASE_URL}/approvals/${approvalId}/approve`, {
    method: "POST",
    headers: companyHeaders(companyId),
  });

  if (!response.ok) {
    throw new Error(`Approval failed with ${response.status}`);
  }

  return response.json();
}

export async function rejectAction(
  approvalId: string,
  reason: string,
  companyId = "",
): Promise<ApprovalActionResult> {
  const response = await fetch(`${API_BASE_URL}/approvals/${approvalId}/reject`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...companyHeaders(companyId),
    },
    body: JSON.stringify({ reason }),
  });

  if (!response.ok) {
    throw new Error(`Reject failed with ${response.status}`);
  }

  return response.json();
}

export async function requestRevision(
  approvalId: string,
  reason: string,
  companyId = "",
): Promise<ApprovalActionResult> {
  const response = await fetch(`${API_BASE_URL}/approvals/${approvalId}/request-revision`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...companyHeaders(companyId),
    },
    body: JSON.stringify({ reason }),
  });

  if (!response.ok) {
    throw new Error(`Revision request failed with ${response.status}`);
  }

  return response.json();
}

export async function getHandoffPreview(
  actionId: string,
  companyId = "",
): Promise<HandoffPreview> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-preview`, {
    headers: companyHeaders(companyId),
  });

  if (!response.ok) {
    throw new Error(`Handoff preview failed with ${response.status}`);
  }

  return response.json();
}

export async function getDocumentRequestDraft(
  actionId: string,
  companyId = "",
): Promise<DocumentRequestDraft> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/document-request-draft`, {
    headers: companyHeaders(companyId),
  });

  if (!response.ok) {
    throw new Error(`Document request draft failed with ${response.status}`);
  }

  return response.json();
}

export async function getCaseEvidenceEvents(
  caseId: string,
  companyId = "",
): Promise<EvidenceEvent[]> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/evidence-events`, {
    headers: companyHeaders(companyId),
  });

  if (!response.ok) {
    throw new Error(`Evidence events failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingSourceSummary(): Promise<DailyBriefingSourceSummary> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/sources/summary`, {
    headers: adminHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Daily briefing source summary failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingSchedulerStatus(): Promise<ScheduledDailyBriefingStatus> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/scheduler/status`, {
    headers: adminHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Daily briefing scheduler status failed with ${response.status}`);
  }

  return response.json();
}

export async function importDailyBriefingSourceCsv(
  payload: DailyBriefingCsvImportPayload,
): Promise<DailyBriefingImportResult> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/sources/import-csv`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Daily briefing CSV import failed with ${response.status}`);
  }

  return response.json();
}

export async function validateDailyBriefingSourceCsv(
  payload: DailyBriefingCsvImportPayload,
): Promise<DailyBriefingCsvValidationReport> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/sources/validate-csv`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Daily briefing CSV validation failed with ${response.status}`);
  }

  return response.json();
}

export async function uploadDailyBriefingSourceCsv(
  sourceType: string,
  file: File,
): Promise<DailyBriefingImportResult> {
  const form = new FormData();
  form.append("source_type", sourceType);
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/daily-briefings/sources/upload-csv`, {
    method: "POST",
    headers: adminHeaders(),
    body: form,
  });
  if (!response.ok) {
    throw new Error(`Daily briefing CSV upload failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingHistory(
  companyId = "",
): Promise<DailyBriefingHistory> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/history/list?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: companyHeaders(companyId),
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing history failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingDataQualitySummary(
  companyId = "",
): Promise<DailyBriefingDataQualitySummary> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/quality/summary?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: companyHeaders(companyId),
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing quality summary failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingPilotMetrics(
  companyId = "",
): Promise<DailyBriefingPilotMetrics> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/metrics/summary?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: companyHeaders(companyId),
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing metrics failed with ${response.status}`);
  }

  return response.json();
}

export async function createDailyBriefingMetricsSnapshot(
  companyId = "",
  date = new Date().toISOString().slice(0, 10),
): Promise<DailyBriefingMetricsSnapshot> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/metrics/snapshot`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders({ companyId }),
    },
    body: JSON.stringify({ company_id: companyId, date }),
  });
  if (!response.ok) {
    throw new Error(`Daily briefing metrics snapshot failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingSchedulerHistory(
  companyId = "",
): Promise<DailyBriefingSchedulerHistory> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/scheduler/history?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: companyHeaders(companyId),
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing scheduler history failed with ${response.status}`);
  }

  return response.json();
}

export async function getHandoffExportDraft(
  actionId: string,
  companyId = "",
): Promise<HandoffExportDraft> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-export-draft`, {
    headers: companyHeaders(companyId),
  });
  if (!response.ok) {
    throw new Error(`Handoff export draft failed with ${response.status}`);
  }

  return response.json();
}

export function getHandoffExportPdfUrl(actionId: string): string {
  return `${API_BASE_URL}/actions/${actionId}/handoff-export.pdf`;
}

export async function downloadHandoffExportPdf(
  actionId: string,
  companyId = "",
): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-export.pdf`, {
    headers: companyHeaders(companyId),
  });
  if (!response.ok) {
    throw new Error(`Handoff export PDF failed with ${response.status}`);
  }

  return response.blob();
}

export async function createExternalDeliveryJob(
  actionId: string,
  companyId = "",
  provider = "manual",
): Promise<ExternalDeliveryJob> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/external-delivery-jobs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...companyHeaders(companyId),
    },
    body: JSON.stringify({ channel: "admin_scrivener", provider }),
  });
  if (!response.ok) {
    throw new Error(`External delivery job failed with ${response.status}`);
  }

  return response.json();
}

export async function dispatchExternalDeliveryJob(
  jobId: string,
  companyId = "",
): Promise<ExternalDeliveryJob> {
  const response = await fetch(`${API_BASE_URL}/external-delivery-jobs/${jobId}/dispatch`, {
    method: "POST",
    headers: companyHeaders(companyId),
  });
  if (!response.ok) {
    throw new Error(`External delivery dispatch failed with ${response.status}`);
  }

  return response.json();
}

export async function getHandoffExportArtifacts(
  actionId: string,
  companyId = "",
): Promise<HandoffExportArtifact[]> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-exports`, {
    headers: companyHeaders(companyId),
  });
  if (!response.ok) {
    throw new Error(`Handoff export artifacts failed with ${response.status}`);
  }

  return response.json();
}

export const SCRIVENER_WORKER_ID = "750e8400-e29b-41d4-a716-446655440001";

export async function createMessageDraftForAction(payload: {
  workerId: string;
  companyId: string;
  messagePurpose: "missing_document_request" | "handoff_notification";
  sourceActionId: string;
  extraContext?: string;
}): Promise<{ id: string; worker: { id: string }; title: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/contact/messages/draft`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...companyHeaders(payload.companyId),
    },
    body: JSON.stringify({
      worker_id: payload.workerId,
      company_id: payload.companyId,
      message_purpose: payload.messagePurpose,
      source_action_id: payload.sourceActionId,
      extra_context: payload.extraContext,
    }),
  });
  if (!response.ok) throw new Error("메시지 초안 생성 실패");
  return response.json();
}

export type AgentReviewResult = {
  action_id: string;
  worker_id: string | null;
  risk_flags: string[];
  summary: string;
  summary_structured: {
    visa_risk?: string;
    visa_d_day?: number | null;
    doc_priority?: string;
    missing_critical?: string[];
    missing_supplementary?: string[];
    visa_risk_flags?: string[];
    doc_risk_flags?: string[];
    submission_readiness?: string;
    action_plan?: string[];
    handoff_triggered?: boolean;
  };
};

export async function runAgentReview(
  actionId: string,
  companyId = "",
): Promise<AgentReviewResult> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/agent-review`, {
    method: "POST",
    headers: companyHeaders(companyId),
  });

  if (!response.ok) {
    throw new Error(`Agent review failed with ${response.status}`);
  }

  return response.json();
}

export type ActionContactThread = {
  id: string;
  worker_id: string;
  title: string;
  status: string;
  source_action_id: string | null;
  last_message_at: string | null;
};

export async function getActionContactThreads(
  actionId: string,
  companyId = "",
): Promise<ActionContactThread[]> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/contact-threads`, {
    headers: companyHeaders(companyId),
  });
  if (!response.ok) return [];
  return response.json();
}

export async function getCaseAuditReview(
  caseId: string,
  companyId = "",
): Promise<CaseAuditReview> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/audit-review`, {
    headers: companyHeaders(companyId),
  });
  if (!response.ok) {
    throw new Error(`Case audit review failed with ${response.status}`);
  }

  return response.json();
}

export async function getCitationDetail(citationId: string): Promise<CitationDetail> {
  const response = await fetch(`${API_BASE_URL}/citations/${citationId}`);
  if (!response.ok) {
    throw new Error(`Citation detail failed with ${response.status}`);
  }

  return response.json();
}

export async function getCitationValidation(citationId: string): Promise<CitationValidationStatus> {
  const response = await fetch(`${API_BASE_URL}/citations/${citationId}/validation`);
  if (!response.ok) {
    throw new Error(`Citation validation failed with ${response.status}`);
  }

  return response.json();
}

export async function getCitationAdminList(
  filters: { missingEvidence?: boolean; staleEvidence?: boolean; syntheticOnly?: boolean } = {},
): Promise<CitationAdminList> {
  const params = new URLSearchParams();
  if (filters.missingEvidence !== undefined) {
    params.set("missing_evidence", String(filters.missingEvidence));
  }
  if (filters.staleEvidence !== undefined) {
    params.set("stale_evidence", String(filters.staleEvidence));
  }
  if (filters.syntheticOnly !== undefined) {
    params.set("synthetic_only", String(filters.syntheticOnly));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/citations/admin/list${suffix}`, {
    headers: adminHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Citation admin list failed with ${response.status}`);
  }

  return response.json();
}

export async function createCitationRefreshQueueItem(
  citationId: string,
  reason: string,
  priority = "medium",
): Promise<CitationRefreshQueue["items"][number]> {
  const response = await fetch(`${API_BASE_URL}/citations/refresh-queue`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
    },
    body: JSON.stringify({ citation_id: citationId, reason, priority }),
  });
  if (!response.ok) {
    throw new Error(`Citation refresh queue creation failed with ${response.status}`);
  }

  return response.json();
}

export async function processCitationRefreshQueueItem(
  queueId: string,
  citationId: string,
): Promise<CitationRefreshQueue["items"][number]> {
  const response = await fetch(`${API_BASE_URL}/citations/refresh-queue/${queueId}/process`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
    },
    body: JSON.stringify({
      refresh_mode: "manual_source",
      citation: {
        title: `Manual refreshed citation: ${citationId}`,
        source_type: "official",
        source: "Operator-reviewed manual source text. External web fetch was not performed.",
        ingest_at: new Date().toISOString(),
        document_id: `doc_${citationId.replace(/^cit_/, "")}_manual`,
        chunk_id: `chunk_${citationId.replace(/^cit_/, "")}_manual`,
        chunk_version: new Date().toISOString().slice(0, 10),
        retrieved_at: new Date().toISOString(),
        source_url: `manual://citation-refresh/${citationId}`,
      },
    }),
  });
  if (!response.ok) {
    throw new Error(`Citation refresh processing failed with ${response.status}`);
  }

  return response.json();
}

export async function getCitationRefreshQueue(status = "open"): Promise<CitationRefreshQueue> {
  const response = await fetch(
    `${API_BASE_URL}/citations/refresh-queue?status=${encodeURIComponent(status)}`,
    {
      headers: adminHeaders(),
    },
  );
  if (!response.ok) {
    throw new Error(`Citation refresh queue failed with ${response.status}`);
  }

  return response.json();
}

export async function getCitationChunk(citationId: string): Promise<CitationChunkView> {
  const response = await fetch(`${API_BASE_URL}/citations/${citationId}/chunk`);
  if (!response.ok) {
    throw new Error(`Citation chunk failed with ${response.status}`);
  }

  return response.json();
}
export async function getCitationSourceDocument(citationId: string): Promise<CitationSourceDocumentView> {
  const response = await fetch(`${API_BASE_URL}/citations/${citationId}/source`);
  if (!response.ok) {
    throw new Error(`Citation source document failed with ${response.status}`);
  }

  return response.json();
}
