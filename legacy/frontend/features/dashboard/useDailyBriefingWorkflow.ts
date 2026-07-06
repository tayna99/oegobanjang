"use client";

import { useCallback, useEffect, useState } from "react";

import {
  approveAction,
  createExternalDeliveryJob,
  dispatchExternalDeliveryJob,
  downloadHandoffExportPdf,
  fetchCompanyList,
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
  ApprovalActionResult,
  CitationChunkView,
  CitationSourceDocumentView,
  CitationValidationStatus,
  DailyBriefingResult,
  DocumentRequestDraft,
  ExternalDeliveryJob,
  HandoffExportArtifact,
  HandoffPreview,
  NextAction,
} from "../../types/dailyBriefing";

export function todayInputValue() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Seoul" });
}

export function useDailyBriefingWorkflow(initialCompanyId = "") {
  const [companyId, setCompanyId] = useState(initialCompanyId);
  const [date, setDate] = useState(todayInputValue);
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

  useEffect(() => {
    if (companyId) return;
    fetchCompanyList().then((list) => {
      if (list.length > 0) setCompanyId(list[0].id);
    });
  }, [companyId]);

  const refreshBriefing = useCallback(() => runDailyBriefing(companyId, date), [companyId, date]);

  const clearOpenViews = useCallback(() => {
    setPreview(null);
    setDocumentDraft(null);
    setDeliveryJob(null);
    setExportArtifacts([]);
    setCitationChunk(null);
    setCitationSource(null);
    setCitationValidation(null);
  }, []);

  const runBriefing = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    setError(null);
    try {
      setBriefing(await refreshBriefing());
      clearOpenViews();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Daily briefing failed");
    } finally {
      setLoading(false);
    }
  }, [clearOpenViews, companyId, refreshBriefing]);

  const approve = useCallback(
    async (action: NextAction) => {
      setError(null);
      try {
        const result = await approveAction(action.approval_id, companyId);
        setBriefing(await refreshBriefing());
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Approval failed");
        return null;
      }
    },
    [companyId, refreshBriefing],
  ) as (action: NextAction) => Promise<ApprovalActionResult | null>;

  const reject = useCallback(
    async (action: NextAction) => {
      setError(null);
      try {
        const result = await rejectAction(action.approval_id, "Rejected during internal review.", companyId);
        setBriefing(await refreshBriefing());
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Reject failed");
        return null;
      }
    },
    [companyId, refreshBriefing],
  ) as (action: NextAction) => Promise<ApprovalActionResult | null>;

  const requestActionRevision = useCallback(
    async (action: NextAction, reason = "Please revise this draft.") => {
      setError(null);
      try {
        const result = await requestRevision(action.approval_id, reason, companyId);
        setBriefing(await refreshBriefing());
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Revision request failed");
        return null;
      }
    },
    [companyId, refreshBriefing],
  ) as (action: NextAction, reason?: string) => Promise<ApprovalActionResult | null>;

  const openHandoffPreview = useCallback(
    async (action: NextAction) => {
      setError(null);
      try {
        setPreview(await getHandoffPreview(action.action_id, companyId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Handoff preview failed");
        setPreview(null);
      }
    },
    [companyId],
  );

  const openDocumentDraft = useCallback(
    async (action: NextAction) => {
      setError(null);
      try {
        setDocumentDraft(await getDocumentRequestDraft(action.action_id, companyId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Document request draft failed");
      }
    },
    [companyId],
  );

  const createDeliveryJob = useCallback(
    async (action: NextAction) => {
      setError(null);
      try {
        const job = await createExternalDeliveryJob(action.action_id, companyId, "mock_webhook");
        setDeliveryJob(job);
        return job;
      } catch (err) {
        setError(err instanceof Error ? err.message : "External delivery job failed");
        return null;
      }
    },
    [companyId],
  );

  const mockDispatch = useCallback(async () => {
    if (!deliveryJob) {
      return;
    }
    setError(null);
    try {
      setDeliveryJob(await dispatchExternalDeliveryJob(deliveryJob.job_id, companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mock dispatch verification failed");
    }
  }, [companyId, deliveryJob]);

  const downloadExport = useCallback(
    async (action: NextAction) => {
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
    },
    [companyId],
  );

  const openCitation = useCallback(async (citationId: string) => {
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
  }, []);

  return {
    approve,
    briefing,
    citationChunk,
    citationSource,
    citationValidation,
    clearOpenViews,
    companyId,
    createDeliveryJob,
    date,
    deliveryJob,
    documentDraft,
    downloadExport,
    error,
    exportArtifacts,
    loading,
    mockDispatch,
    openCitation,
    openDocumentDraft,
    openHandoffPreview,
    preview,
    refreshBriefing,
    reject,
    requestActionRevision,
    runBriefing,
    setCitationChunk,
    setCitationSource,
    setCitationValidation,
    setDeliveryJob,
    setDocumentDraft,
    setPreview,
  };
}
