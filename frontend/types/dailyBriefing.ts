export type RiskSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type RiskSummary = {
  total_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  by_risk_type: Record<string, number>;
};

export type DailyBriefingItem = {
  item_id: string;
  case_id: string;
  subject_type: "worker" | "company" | "case" | "candidate";
  subject_id: string;
  subject_display_name: string | null;
  subject_display_id: string | null;
  risk_type:
    | "visa_expiry"
    | "missing_document"
    | "contract_visa_conflict"
    | "reporting_deadline"
    | "quota_review"
    | "candidate_readiness"
    | "worker_reply";
  severity: RiskSeverity;
  d_day: number | null;
  expired: boolean;
  days_overdue: number | null;
  risk_timing_label: string | null;
  case_title: string | null;
  case_summary: string | null;
  primary_action: NextAction | null;
  source_labels: string[];
  missing_documents: string[];
  citation_ids: string[];
  next_action_ids: string[];
};

export type NextAction = {
  action_id: string;
  case_id: string;
  approval_id: string;
  action_type: "request_document" | "create_handoff";
  status:
    | "pending_approval"
    | "approved"
    | "rejected"
    | "revision_requested"
    | "blocked"
    | "completed"
    | "cancelled";
  subject_id: string;
  label: string;
  approval_required: boolean;
  blocked_until_approved: boolean;
  evidence_required: boolean;
  citation_ids: string[];
  approved_at: string | null;
};

export type ApprovalActionResult = {
  approval_id: string;
  action_id: string;
  status: string;
  approved_at: string;
  evidence_event_id: string;
};

export type CitationSummary = {
  citation_id: string;
  title: string;
  source_type: "official" | "internal" | "synthetic";
  source: string;
  ingest_at: string;
  document_id: string | null;
  chunk_id: string | null;
  chunk_version: string | null;
  retrieved_at: string | null;
  source_url: string | null;
  validation_status:
    | "not_checked"
    | "validated"
    | "missing_evidence"
    | "validation_error"
    | "stale_evidence"
    | "synthetic_only";
  missing_evidence: boolean;
  retrieved_source_ids: string[];
  evidence_grade: string | null;
  validation_reason: string | null;
  stale_evidence: boolean;
  synthetic_only: boolean;
  policy_update_needed: boolean;
};

export type CitationDetail = CitationSummary;

export type DailyBriefingResult = {
  briefing_run_id: string;
  company_id: string;
  date: string;
  generated_at: string;
  timezone: string;
  source_snapshot_hash: string;
  rerun_count: number;
  last_refreshed_at: string;
  items: DailyBriefingItem[];
  risk_summary: RiskSummary;
  recommended_actions: NextAction[];
  citation_summaries: CitationSummary[];
  evidence_event_ids: string[];
  approval_required: boolean;
};

export type AgentChatToolCall = {
  name: string;
  route: string;
  intent: string;
  result_count: number;
  action_count: number;
  source_count: number;
};

export type AgentChatStructuredPlan = {
  should_run: boolean;
  intent: string | null;
  plan_steps: string[];
  required_context: string[];
  entities: Record<string, string>;
  blocked_actions: string[];
  approval_required: boolean;
  execution_allowed: boolean;
  target_service: string | null;
};

export type AgentChatExecutedTool = {
  name: string;
  intent: string;
  result_count: number;
  action_count: number;
  source_count: number;
  rag_hit_count: number;
};

export type AgentChatRagHit = {
  chunk_id: string | null;
  source_id: string | null;
  title: string | null;
  source_type: "official_policy" | "operational_case" | "action_draft" | "evidence_event" | string;
  intent: string | null;
  risk_type: string | null;
  case_id: string | null;
  citation_ids: string[];
  action_ids: string[];
  score: number | null;
};

export type AgentChatContactPreview = {
  kind:
    | "message_draft"
    | "worker_reply_summary"
    | "worker_reply_summary_required_input"
    | string;
  language_code?: string | null;
  message_purpose?: string | null;
  status?: string | null;
  korean_text?: string | null;
  translated_text?: string | null;
  summary_ko?: string | null;
  status_update_candidate_count?: number;
  sent?: boolean;
  status_applied?: boolean;
  external_send_performed?: boolean;
  approval_required?: boolean;
  manager_review_required?: boolean;
  required_input?: string | null;
};

export type AgentChatContactSubagentSummary = {
  status: string;
  approval_required: boolean;
  approval_status: string;
  manager_review_required?: boolean;
  status_update_candidate_count?: number;
  risk_flags?: string[];
};

export type AgentChatResponse = {
  answer: string;
  final_response: string;
  route: string;
  orchestration_version?: string;
  normalized_intent?: string;
  normalized_entities?: Record<string, string>;
  executed_tools?: AgentChatExecutedTool[];
  llm_used: boolean;
  latency_mode: string;
  tool_calls: AgentChatToolCall[];
  actions: NextAction[];
  sources: CitationSummary[];
  subject_display_name?: string | null;
  subject_display_id?: string | null;
  risk_timing_label?: string | null;
  case_title?: string | null;
  case_summary?: string | null;
  primary_action?: NextAction | null;
  source_labels?: string[];
  detected_intents: string[];
  approval_required: boolean;
  approval_status: string;
  daily_briefing?: DailyBriefingResult;
  structured_plan: AgentChatStructuredPlan;
  rag_hits?: AgentChatRagHit[];
  retrieval_source_types?: string[];
  llm_provider?: string | null;
  fallback_used?: boolean;
  fallback_reason?: string | null;
  contact_preview?: AgentChatContactPreview | null;
  contact_subagents?: Record<string, AgentChatContactSubagentSummary>;
  agent_used?: string;
  rag_collections_used?: string[];
  agent_sub_agents?: string[];
};

export type HandoffPreview = {
  preview_id: string;
  case_id: string;
  action_id: string;
  content_redacted: Record<string, unknown> | string;
  citation_ids: string[];
  warning_flags: string[];
  created_at: string;
};

export type DocumentRequestDraft = {
  draft_id: string;
  case_id: string;
  action_id: string;
  worker_id: string;
  status: "preview_only";
  approval_required: boolean;
  external_send_performed: boolean;
  missing_documents: string[];
  korean_text: string;
  translated_text: string;
  language_code: string;
  citation_ids: string[];
  warning_flags: string[];
  created_at: string;
};

export type HandoffExportDraft = {
  export_id: string;
  case_id: string;
  action_id: string;
  format: "markdown";
  approval_status: string;
  external_delivery_performed: boolean;
  content_markdown: string;
  citation_ids: string[];
  warning_flags: string[];
  evidence_event_id: string;
  created_at: string;
};

export type ExternalDeliveryJob = {
  job_id: string;
  case_id: string;
  action_id: string;
  channel: string;
  provider: string;
  status: "pending_manual_dispatch" | "mock_dispatched" | "sent";
  external_send_performed: boolean;
  payload_redacted: Record<string, unknown>;
  citation_ids: string[];
  warning_flags: string[];
  evidence_event_id: string;
  provider_message_id: string | null;
  created_at: string;
};

export type HandoffExportArtifact = {
  artifact_id: string;
  case_id: string;
  action_id: string;
  format: "pdf" | "markdown";
  content_hash: string;
  download_url: string;
  external_delivery_performed: boolean;
  evidence_event_id: string;
  created_at: string;
};

export type CitationChunkView = {
  viewer_kind: "chunk";
  citation_id: string;
  document_id: string | null;
  chunk_id: string | null;
  chunk_version: string | null;
  retrieved_at: string | null;
  source_url: string | null;
  source_type: string;
  chunk_text: string;
  download_available: boolean;
};

export type CitationSourceDocumentView = {
  viewer_kind: "source_document";
  citation_id: string;
  document_id: string | null;
  title: string;
  source_type: string;
  source_url: string | null;
  retrieved_at: string | null;
  chunk_ids: Array<string | null>;
  download_available: boolean;
  original_pdf_available: boolean;
};

export type CitationValidationStatus = {
  citation_id: string;
  validation_status: string;
  validation_reason: string;
  missing_evidence: boolean;
  stale_evidence: boolean;
  synthetic_only: boolean;
  policy_update_needed: boolean;
  source_type: string;
  document_id: string | null;
  chunk_id: string | null;
  chunk_version: string | null;
  retrieved_at: string | null;
};

export type DailyBriefingSourceSummary = {
  status: "ready";
  source_counts: {
    companies: number;
    workers: number;
    documents: number;
    candidates: number;
    candidate_documents: number;
    reporting_events: number;
    citations: number;
    user_company_access: number;
  };
  pii_policy: string;
};

export type ScheduledDailyBriefingStatus = {
  enabled: boolean;
  run_on_startup: boolean;
  interval_seconds: number;
  timezone: string;
  configured_company_ids: string[] | null;
  running: boolean;
  last_run: {
    status: string;
    run_date: string;
    total_companies: number;
    succeeded_count: number;
    failed_count: number;
    briefing_run_ids: string[];
    errors: Array<Record<string, unknown>>;
  } | null;
};

export type DailyBriefingHistoryRun = {
  briefing_run_id: string;
  company_id: string;
  date: string;
  total_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  approval_pending_count: number;
  missing_evidence_count: number;
  source_snapshot_hash: string;
  updated_at: string;
};

export type DailyBriefingHistory = {
  total_count: number;
  runs: DailyBriefingHistoryRun[];
};

export type DailyBriefingPilotMetrics = {
  company_id: string | null;
  briefing_run_count: number;
  approval_count: number;
  approved_count: number;
  revision_requested_count: number;
  rejected_count: number;
  approval_rate: number;
  revision_rate: number;
  rejection_rate: number;
  handoff_export_count: number;
  mock_dispatch_count: number;
  missing_evidence_count: number;
  high_or_critical_risk_count: number;
};

export type DailyBriefingCsvImportPayload = {
  companies_csv?: string;
  workers_csv?: string;
  documents_csv?: string;
  candidates_csv?: string;
  candidate_documents_csv?: string;
  reporting_events_csv?: string;
  citations_csv?: string;
  user_company_access_csv?: string;
};

export type DailyBriefingImportResult = {
  upserted_counts: Record<string, number>;
};

export type DailyBriefingCsvValidationReport = {
  status: "valid" | "invalid";
  issue_count: number;
  warning_count: number;
  row_counts: Record<string, number>;
  issues: Array<{
    source_type: string;
    row_number: number;
    issue_type: string;
    message: string;
  }>;
  warnings: Array<Record<string, unknown>>;
  pii_policy: string;
};

export type DailyBriefingDataQualitySummary = {
  company_id: string | null;
  worker_count: number;
  missing_visa_expiry_count: number;
  missing_contract_end_count: number;
  orphan_document_count: number;
  citation_gap_count: number;
  issues: Array<{ issue_type: string; severity: string; count: number }>;
  pii_policy: string;
};

export type DailyBriefingMetricsSnapshot = {
  snapshot_id: string;
  company_id: string | null;
  snapshot_date: string;
  metrics: DailyBriefingPilotMetrics;
  created_at: string;
};

export type DailyBriefingSchedulerHistory = {
  total_count: number;
  runs: Array<{
    run_id: string;
    date: string;
    status: string;
    company_ids: string[];
    total_companies: number;
    succeeded_count: number;
    failed_count: number;
    created_at: string;
  }>;
};

export type CitationRefreshQueue = {
  total_count: number;
  items: Array<{
    queue_id: string;
    citation_id: string;
    reason: string;
    priority: string;
    status: string;
    external_fetch_performed: boolean;
    created_at: string;
  }>;
};

export type CitationAdminList = {
  total_count: number;
  items: CitationDetail[];
};

export type EvidenceEvent = {
  event_id: string;
  event_version: "v1";
  trace_id: string;
  case_id: string | null;
  request_id: string | null;
  event_type: string;
  actor_type: string;
  node_name: string;
  summary: string;
  citation_ids: string[];
  redacted_input_hash: string | null;
  redacted_output_hash: string | null;
  hash_algorithm: "sha256";
  payload_ref: string | null;
  created_at: string;
};

export type CaseAuditReview = {
  case: {
    case_id: string;
    company_id: string;
    worker_id: string | null;
    risk_type: string;
    status: string;
    due_date: string | null;
    risk_level: RiskSeverity;
    created_at: string;
    updated_at: string;
  };
  rule_snapshot: Record<string, unknown>;
  db_snapshot: Record<string, unknown>;
  source_snapshot_hash: string | null;
  briefing_run_id: string | null;
  actions: NextAction[];
  approval_history: Array<Record<string, unknown>>;
  citation_details: CitationDetail[];
  evidence_events: EvidenceEvent[];
};
