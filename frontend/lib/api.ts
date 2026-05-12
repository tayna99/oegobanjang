import type {
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

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

export async function runDailyBriefing(
  companyId = "company_001",
  date = "2026-05-08",
): Promise<DailyBriefingResult> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Company-Id": companyId,
      "X-User-Role": "manager",
      "X-User-Id": "manager_001",
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
  companyId = "company_001",
  workspaceId,
  activeTab = "today",
  selectedCaseId,
  sessionId,
}: {
  message: string;
  companyId?: string;
  workspaceId?: string;
  activeTab?: string;
  selectedCaseId?: string;
  sessionId?: string;
}): Promise<AgentChatResponse> {
  const response = await fetch(`${API_BASE_URL}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Company-Id": companyId,
      "X-User-Role": "manager",
      "X-User-Id": "manager_001",
    },
    body: JSON.stringify({
      message,
      companyId,
      workspaceId,
      activeTab,
      selectedCaseId,
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
  companyId = "company_001",
): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/approvals/${approvalId}/approve`, {
    method: "POST",
    headers: {
      "X-Company-Id": companyId,
      "X-User-Role": "manager",
      "X-User-Id": "manager_001",
    },
  });

  if (!response.ok) {
    throw new Error(`Approval failed with ${response.status}`);
  }

  return response.json();
}

export async function rejectAction(
  approvalId: string,
  reason: string,
  companyId = "company_001",
): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/approvals/${approvalId}/reject`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Company-Id": companyId,
      "X-User-Role": "manager",
      "X-User-Id": "manager_001",
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
  companyId = "company_001",
): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/approvals/${approvalId}/request-revision`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Company-Id": companyId,
      "X-User-Role": "manager",
      "X-User-Id": "manager_001",
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
  companyId = "company_001",
): Promise<HandoffPreview> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-preview`, {
    headers: {
      "X-Company-Id": companyId,
    },
  });

  if (!response.ok) {
    throw new Error(`Handoff preview failed with ${response.status}`);
  }

  return response.json();
}

export async function getDocumentRequestDraft(
  actionId: string,
  companyId = "company_001",
): Promise<DocumentRequestDraft> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/document-request-draft`, {
    headers: {
      "X-Company-Id": companyId,
    },
  });

  if (!response.ok) {
    throw new Error(`Document request draft failed with ${response.status}`);
  }

  return response.json();
}

export async function getCaseEvidenceEvents(
  caseId: string,
  companyId = "company_001",
): Promise<EvidenceEvent[]> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/evidence-events`, {
    headers: {
      "X-Company-Id": companyId,
    },
  });

  if (!response.ok) {
    throw new Error(`Evidence events failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingSourceSummary(): Promise<DailyBriefingSourceSummary> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/sources/summary`, {
    headers: {
      "X-User-Role": "admin",
    },
  });
  if (!response.ok) {
    throw new Error(`Daily briefing source summary failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingSchedulerStatus(): Promise<ScheduledDailyBriefingStatus> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/scheduler/status`, {
    headers: {
      "X-User-Role": "admin",
    },
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
      "X-User-Role": "admin",
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
      "X-User-Role": "admin",
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
    headers: {
      "X-User-Role": "admin",
    },
    body: form,
  });
  if (!response.ok) {
    throw new Error(`Daily briefing CSV upload failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingHistory(
  companyId = "company_001",
): Promise<DailyBriefingHistory> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/history/list?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: {
        "X-Company-Id": companyId,
      },
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing history failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingDataQualitySummary(
  companyId = "company_001",
): Promise<DailyBriefingDataQualitySummary> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/quality/summary?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: {
        "X-Company-Id": companyId,
      },
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing quality summary failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingPilotMetrics(
  companyId = "company_001",
): Promise<DailyBriefingPilotMetrics> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/metrics/summary?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: {
        "X-Company-Id": companyId,
      },
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing metrics failed with ${response.status}`);
  }

  return response.json();
}

export async function createDailyBriefingMetricsSnapshot(
  companyId = "company_001",
  date = "2026-05-08",
): Promise<DailyBriefingMetricsSnapshot> {
  const response = await fetch(`${API_BASE_URL}/daily-briefings/metrics/snapshot`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Company-Id": companyId,
      "X-User-Role": "admin",
    },
    body: JSON.stringify({ company_id: companyId, date }),
  });
  if (!response.ok) {
    throw new Error(`Daily briefing metrics snapshot failed with ${response.status}`);
  }

  return response.json();
}

export async function getDailyBriefingSchedulerHistory(
  companyId = "company_001",
): Promise<DailyBriefingSchedulerHistory> {
  const response = await fetch(
    `${API_BASE_URL}/daily-briefings/scheduler/history?company_id=${encodeURIComponent(companyId)}`,
    {
      headers: {
        "X-Company-Id": companyId,
      },
    },
  );
  if (!response.ok) {
    throw new Error(`Daily briefing scheduler history failed with ${response.status}`);
  }

  return response.json();
}

export async function getHandoffExportDraft(
  actionId: string,
  companyId = "company_001",
): Promise<HandoffExportDraft> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-export-draft`, {
    headers: {
      "X-Company-Id": companyId,
    },
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
  companyId = "company_001",
): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-export.pdf`, {
    headers: {
      "X-Company-Id": companyId,
    },
  });
  if (!response.ok) {
    throw new Error(`Handoff export PDF failed with ${response.status}`);
  }

  return response.blob();
}

export async function createExternalDeliveryJob(
  actionId: string,
  companyId = "company_001",
  provider = "manual",
): Promise<ExternalDeliveryJob> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/external-delivery-jobs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Company-Id": companyId,
      "X-User-Role": "manager",
      "X-User-Id": "manager_001",
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
  companyId = "company_001",
): Promise<ExternalDeliveryJob> {
  const response = await fetch(`${API_BASE_URL}/external-delivery-jobs/${jobId}/dispatch`, {
    method: "POST",
    headers: {
      "X-Company-Id": companyId,
      "X-User-Role": "manager",
      "X-User-Id": "manager_001",
    },
  });
  if (!response.ok) {
    throw new Error(`External delivery dispatch failed with ${response.status}`);
  }

  return response.json();
}

export async function getHandoffExportArtifacts(
  actionId: string,
  companyId = "company_001",
): Promise<HandoffExportArtifact[]> {
  const response = await fetch(`${API_BASE_URL}/actions/${actionId}/handoff-exports`, {
    headers: {
      "X-Company-Id": companyId,
    },
  });
  if (!response.ok) {
    throw new Error(`Handoff export artifacts failed with ${response.status}`);
  }

  return response.json();
}

export async function getCaseAuditReview(
  caseId: string,
  companyId = "company_001",
): Promise<CaseAuditReview> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/audit-review`, {
    headers: {
      "X-Company-Id": companyId,
    },
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
    headers: {
      "X-User-Role": "admin",
    },
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
      "X-User-Role": "admin",
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
      "X-User-Role": "admin",
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
      headers: {
        "X-User-Role": "admin",
      },
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

export async function getCitationSourceDocument(
  citationId: string,
): Promise<CitationSourceDocumentView> {
  const response = await fetch(`${API_BASE_URL}/citations/${citationId}/source-document`);
  if (!response.ok) {
    throw new Error(`Citation source document failed with ${response.status}`);
  }

  return response.json();
}
