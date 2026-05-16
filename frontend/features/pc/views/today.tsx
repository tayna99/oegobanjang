import {
  Check,
  CheckCircle,
  Download,
  FileText,
  MessageSquare,
  MoreHorizontal,
  Search,
  UserRoundPlus,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import type { DailyBriefingItem, DailyBriefingResult } from "../../../types/dailyBriefing";
import type { AgentReviewResult } from "../../../lib/api";
import { createMessageDraftForAction, runAgentReview } from "../../../lib/api";
import { adminPackage, contactItems, judgmentRows, workers, type Tone } from "../data";
import { Badge, Button, Card, cn, PillButton, textToneClass, toneClass } from "../ui";
import styles from "../PcShell.module.css";

const summaryConfig = [
  {
    id: "all", label: "전체", unit: "건",
    color: "#1D4ED8", bg: "#EFF6FF",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M4 6h16M4 12h16M4 18h10" stroke="#1D4ED8" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "visa", label: "체류기간 임박", unit: "건",
    color: "#EF4444", bg: "#FEF2F2",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="#EF4444" strokeWidth="1.8"/><path d="M12 7v5l3 3" stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "docs", label: "서류 보완 필요", unit: "건",
    color: "#F97316", bg: "#FFF7ED",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="#F97316" strokeWidth="1.8" strokeLinejoin="round"/><path d="M14 2v6h6M12 12v4M12 10h.01" stroke="#F97316" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "reply", label: "응답 도착", unit: "건",
    color: "#0EA5E9", bg: "#F0F9FF",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="#0EA5E9" strokeWidth="1.8" strokeLinejoin="round"/><path d="M8 10h8M8 14h4" stroke="#0EA5E9" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "approval", label: "승인 대기", unit: "건",
    color: "#F59E0B", bg: "#FFFBEB",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="#F59E0B" strokeWidth="1.8" strokeLinejoin="round"/></svg>),
  },
];
export type PcActionKind =
  | "refresh"
  | "document-draft"
  | "handoff-preview"
  | "approval-preview"
  | "revision-request"
  | "response-summary"
  | "worker-register"
  | "pdf-draft"
  | "open-ai";

export type PcViewAction = {
  kind: PcActionKind;
  label: string;
  source?: "today_queue";
  targetView?: "contact" | "hiring";
  subjectId?: string | null;
  subjectName?: string | null;
  riskType?: string | null;
};

export type PcViewProps = {
  onAction?: (action: PcViewAction) => void;
};

type TodayTasksViewProps = PcViewProps & {
  briefing?: DailyBriefingResult | null;
  loading?: boolean;
  onNavigateToMessages?: (threadId: string, tab?: "worker" | "expert") => void;
};

type WorkerDocumentRequest = {
  worker_id: string;
  doc_type: string;
  label?: string;
  status?: string;
};

const agentReviewCache = new Map<string, AgentReviewResult>();

const TASK_STATUS_MAP: Record<string, { label: string; bg: string; fg: string }> = {
  "승인 필요": { label: "승인 필요", bg: "#FFF7ED", fg: "#C2410C" },
  "진행 중":   { label: "진행 중",   bg: "#EFF6FF", fg: "#1D4ED8" },
  "승인 대기": { label: "승인 대기", bg: "#FFF7ED", fg: "#C2410C" },
  "응답 도착": { label: "응답 도착", bg: "#ECFDF5", fg: "#065F46" },
  "검토 필요": { label: "검토 필요", bg: "#FFFBEB", fg: "#B45309" },
};

const TASK_TYPE_ICON: Record<string, React.ReactElement> = {
  doc: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M12 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6l-4-4z" stroke="#1B3FA0" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M12 2v4h4M8 10h4M8 13h2" stroke="#1B3FA0" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  hiring: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <circle cx="8" cy="6" r="3" stroke="#10B981" strokeWidth="1.5"/>
      <path d="M3 17c0-3 2-4.5 5-4.5s5 1.5 5 4.5" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M14 3l1.5 1.5L18 2" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  message: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M3 3h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H5l-3 3V4a1 1 0 0 1 1-1z" stroke="#8B5CF6" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  ),
};

const CASE_SEV: Record<string, { bg: string; bd: string; fg: string; dot: string }> = {
  red:    { bg: "rgba(255,66,66,0.10)",   bd: "rgba(255,66,66,0.32)",   fg: "#B00C0C", dot: "#FF4242" },
  orange: { bg: "rgba(255,146,0,0.10)",   bd: "rgba(255,146,0,0.30)",   fg: "#9C5800", dot: "#FF9200" },
  blue:   { bg: "rgba(0,102,255,0.07)",   bd: "rgba(0,102,255,0.20)",   fg: "#003699", dot: "#0066FF" },
  gray:   { bg: "rgba(112,115,124,0.06)", bd: "rgba(112,115,124,0.20)", fg: "#70737C", dot: "#B0B3BA" },
};

const statusPriority: Record<string, number> = {
  "즉시 확인": 5,
  "우선 확인": 4,
  "확인 필요": 3,
  "응답 도착": 2,
  "승인 필요": 1,
  "참고": 0,
};

function workerTestId(workerId: string) {
  return `worker-row-${workerId.replace("w_", "")}`;
}

function itemMatchesSummary(item: DailyBriefingItem, summaryId: string) {
  if (summaryId === "all") {
    return true;
  }
  if (summaryId === "visa") {
    return item.risk_type === "visa_expiry" || item.risk_type === "contract_visa_conflict" || item.risk_type === "reporting_deadline";
  }
  if (summaryId === "docs") {
    return item.risk_type === "missing_document";
  }
  if (summaryId === "reply") {
    return item.risk_type === "worker_reply" || item.case_title?.includes("응답") || item.case_summary?.includes("응답") || false;
  }
  if (summaryId === "approval") {
    return item.primary_action?.status === "pending_approval" || item.primary_action?.approval_required === true;
  }
  return true;
}

function severityLabel(item: DailyBriefingItem) {
  if (item.risk_type === "worker_reply") return "응답 도착";
  if (item.expired || item.severity === "CRITICAL") return "즉시 확인";
  if (item.severity === "HIGH") return "우선 확인";
  if (item.severity === "MEDIUM") return "확인 필요";
  if (item.primary_action?.status === "pending_approval") return "승인 필요";
  return "참고";
}

function twoLineStatusLabel(label: string) {
  return label;
}

function deadlineLabel(item: DailyBriefingItem) {
  if (item.expired && item.days_overdue != null) return `D+${item.days_overdue}`;
  if (item.d_day != null) return item.d_day < 0 ? `D+${Math.abs(item.d_day)}` : `D-${item.d_day}`;
  return item.risk_timing_label ?? "확인 필요";
}

function nextActionForItem(item: DailyBriefingItem, selectedSummaryId: string): PcViewAction {
  const subjectName = item.subject_display_name ?? item.subject_display_id ?? item.subject_id;
  if (selectedSummaryId === "approval" && item.primary_action?.approval_required) {
    return {
      kind: "approval-preview",
      label: "승인 요청",
      source: "today_queue",
      targetView: "hiring",
      subjectId: item.subject_id,
      subjectName,
      riskType: item.risk_type,
    };
  }
  if (item.risk_type === "worker_reply" || item.case_title?.includes("응답") || item.case_summary?.includes("응답")) {
    return {
      kind: "response-summary",
      label: "응답 요약",
      source: "today_queue",
      targetView: "contact",
      subjectId: item.subject_id,
      subjectName,
      riskType: item.risk_type,
    };
  }
  if (item.primary_action?.action_type === "request_document" || item.risk_type === "missing_document") {
    return {
      kind: "document-draft",
      label: "초안 보기",
      source: "today_queue",
      targetView: "contact",
      subjectId: item.subject_id,
      subjectName,
      riskType: item.risk_type,
    };
  }
  if (item.primary_action?.action_type === "create_handoff") {
    return {
      kind: "handoff-preview",
      label: "요청서 보기",
      source: "today_queue",
      subjectId: item.subject_id,
      subjectName,
      riskType: item.risk_type,
    };
  }
  return {
    kind: "handoff-preview",
    label: item.risk_type === "candidate_readiness" ? "요청서 보기" : "요청서 보기",
    source: "today_queue",
    subjectId: item.subject_id,
    subjectName,
    riskType: item.risk_type,
  };
}

function groupItemsBySubject(items: DailyBriefingItem[]) {
  const groups = new Map<string, DailyBriefingItem[]>();
  for (const item of items) {
    const key = item.subject_type === "worker" ? item.subject_id : item.item_id;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return [...groups.values()].map((groupItems) => {
    const sorted = [...groupItems].sort((a, b) => {
      const statusDelta = (statusPriority[severityLabel(b)] ?? 0) - (statusPriority[severityLabel(a)] ?? 0);
      if (statusDelta !== 0) return statusDelta;
      return (b.primary_action?.approval_required ? 1 : 0) - (a.primary_action?.approval_required ? 1 : 0);
    });
    const primary = sorted[0];
    return {
      primary,
      items: sorted,
      statuses: [...new Set(sorted.map(severityLabel))],
      titles: [...new Set(sorted.map((item) => item.case_title ?? item.risk_type))],
    };
  });
}

export function TodayTasksView({ briefing, loading = false, onAction, onNavigateToMessages }: TodayTasksViewProps = {}) {
  const [selectedWorkerId, setSelectedWorkerId] = useState<string | null>(null);
  const [selectedSummaryId, setSelectedSummaryId] = useState("all");
  const [detailOpen, setDetailOpen] = useState(false);
  const [replyItems, setReplyItems] = useState<DailyBriefingItem[]>([]);
  const selectedWorker = workers.find((worker) => worker.id === selectedWorkerId) ?? null;
  const [documentRequestsByWorker, setDocumentRequestsByWorker] = useState<Record<string, WorkerDocumentRequest[]>>({});
  useEffect(() => {
    void loadReplyItems();
    const timer = window.setInterval(() => {
      void loadReplyItems();
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  async function loadReplyItems() {
    try {
      const response = await fetch("/api/v1/contact/threads?company_id=550e8400-e29b-41d4-a716-446655440001", { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      const threads = data.threads ?? [];
      const detailed = await Promise.all(
        threads.map(async (thread: { id: string }) => {
          const detailResponse = await fetch(`/api/v1/contact/threads/${thread.id}`, { cache: "no-store" });
          return detailResponse.ok ? detailResponse.json() : null;
        }),
      );
      const nextItems = detailed.flatMap((thread: {
        id: string;
        worker?: { id?: string; name?: string };
        messages?: Array<{ id: string; direction: string; status: string; created_at?: string; attachments?: unknown[] }>;
      } | null) => {
        if (!thread) return [];
        return (thread.messages ?? [])
          .filter((message) => message.direction === "INBOUND")
          .map((message) => ({
            item_id: `contact_reply_${message.id}`,
            case_id: thread.id,
            subject_type: "worker" as const,
            subject_id: thread.worker?.id ?? "",
            subject_display_name: thread.worker?.name ?? "근로자",
            subject_display_id: thread.worker?.id ?? null,
            risk_type: "worker_reply" as const,
            severity: "LOW" as const,
            d_day: null,
            expired: false,
            days_overdue: null,
            risk_timing_label: "응답 도착",
            case_title: "근로자 응답 도착",
            case_summary: message.attachments?.length ? "근로자가 요청 서류를 업로드했습니다." : "근로자 응답이 도착했습니다.",
            primary_action: null,
            source_labels: ["메시지 관리"],
            missing_documents: [],
            citation_ids: [],
            next_action_ids: [],
          }));
      });
      setReplyItems(nextItems);
    } catch {
      setReplyItems([]);
    }
  }

  useEffect(() => {
    void loadSubmittedDocuments();
    const timer = window.setInterval(() => {
      void loadSubmittedDocuments();
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  async function loadSubmittedDocuments() {
    try {
      const response = await fetch("/api/v1/documents/worker-requests/all?company_id=550e8400-e29b-41d4-a716-446655440001", { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      const requests = (data.requests ?? []) as WorkerDocumentRequest[];
      const groupedRequests = requests.reduce<Record<string, WorkerDocumentRequest[]>>((acc, request) => {
        acc[request.worker_id] = [...(acc[request.worker_id] ?? []), request];
        return acc;
      }, {});
      setDocumentRequestsByWorker(groupedRequests);
    } catch {
      setDocumentRequestsByWorker({});
    }
  }

  const items = useMemo(() => {
    const baseItems = briefing?.items ?? [];
    const existingIds = new Set(baseItems.map((item) => item.item_id));
    return [...baseItems, ...replyItems.filter((item) => !existingIds.has(item.item_id))];
  }, [briefing?.items, replyItems]);
  const filteredItems = items.filter((item) => itemMatchesSummary(item, selectedSummaryId));
  const groupedItems = groupItemsBySubject(filteredItems);
  const summary = summaryConfig.map((item) => ({
    ...item,
    count: groupItemsBySubject(items.filter((briefingItem) => itemMatchesSummary(briefingItem, item.id))).length,
  }));

  function selectSummary(item: (typeof summaryConfig)[number]) {
    setSelectedSummaryId(item.id);
    setSelectedWorkerId(null);
    setDetailOpen(false);
  }

  function selectWorker(workerId: string) {
    setSelectedWorkerId(workerId);
    setDetailOpen(true);
  }

  return (
    <div className={cn(styles.todayDashboard, !detailOpen && styles.todayDashboardCollapsed)}>
      <section className={styles.stack}>

        {/* 요약 카드 */}
        <div className={styles.summaryGrid}>
          {summary.map((item) => (
            <button
              className={cn(styles.card, styles.summaryButton, selectedSummaryId === item.id && styles.summaryButtonActive)}
              data-testid={`summary-${item.id}`}
              key={item.id}
              onClick={() => selectSummary(item)}
              type="button"
              style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10, textAlign: "left" }}
            >
              <div className={styles.summaryIconTile} style={{ background: item.bg }}>
                {item.icon}
              </div>
              <div>
                <div className={styles.summaryLabel}>{item.label}</div>
                <div style={{ display: "flex", alignItems: "baseline" }}>
                  <span className={styles.summaryCount} style={{ color: item.color }}>{item.count}</span>
                  <span className={styles.summaryUnit}>{item.unit}</span>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* 업무 큐 */}
        <div className={styles.taskQueueWrap}>
          <div className={styles.taskQueueHead}>
            오늘의 업무 큐
            <span className={styles.taskQueueHeadCount}>{loading ? "불러오는 중" : `${groupedItems.length}명 / ${filteredItems.length}건`}</span>
          </div>
          <div className={styles.taskQueue}>
            <div className={styles.taskQueueHeader}>
              <div />
              <div>업무</div>
              <div>대상</div>
              <div className={styles.taskStatusHeader}>상태</div>
              <div>기한</div>
              <div>다음 처리</div>
              <div />
            </div>
            {groupedItems.map((group) => {
              const item = group.primary;
              const status = severityLabel(item);
              const deadline = deadlineLabel(item);
              const nextAction = nextActionForItem(item, selectedSummaryId);
              const st = TASK_STATUS_MAP[status] ?? { label: status, bg: "#F8FAFC", fg: "#64748B" };
              const isUrgent = item.expired || item.severity === "CRITICAL" || item.severity === "HIGH";
              const matchedWorker = item.subject_type === "worker" ? workers.find((worker) => worker.id === item.subject_id) : null;
              const isSelected = !!matchedWorker && selectedWorkerId === matchedWorker.id;
              return (
                <div
                  key={item.item_id}
                  className={cn(styles.taskQueueRow, isSelected && styles.taskQueueRowSelected)}
                  onClick={() => { if (matchedWorker) selectWorker(matchedWorker.id); }}
                >
                  <div className={styles.taskCheckbox} />
                  <div className={styles.taskTitleCell}>
                    <div className={styles.taskTypeIcon}>{item.risk_type === "worker_reply" ? TASK_TYPE_ICON.message : TASK_TYPE_ICON.doc}</div>
                    <span className={styles.taskTitle}>
                      {group.titles[0]}
                      {group.titles.length > 1 ? <span className={styles.subtle}> 외 {group.titles.length - 1}건</span> : null}
                    </span>
                  </div>
                  <div className={styles.taskTarget}>{item.subject_display_name ?? item.subject_display_id ?? item.subject_id}</div>
                  <div className={styles.taskStatusStack}>
                    {group.statuses.slice(0, 2).map((statusLabel) => {
                      const statusStyle = TASK_STATUS_MAP[statusLabel] ?? st;
                      return (
                        <span className={styles.taskStatusPill} key={statusLabel} style={{ background: statusStyle.bg, color: statusStyle.fg }}>
                          {twoLineStatusLabel(statusLabel)}
                        </span>
                      );
                    })}
                  </div>
                  <div className={isUrgent ? styles.taskDeadlineUrgent : styles.taskDeadlineNormal}>{deadline}</div>
                  <button
                    className={styles.taskNextBtn}
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onAction?.(nextAction); }}
                  >
                    {nextAction.label}
                  </button>
                  <button className={styles.taskMoreBtn} type="button"><MoreHorizontal size={14} /></button>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {detailOpen && selectedWorker ? (
        <TodayWorkerDetail
          onAction={onAction}
          onClose={() => setDetailOpen(false)}
          onNavigateToMessages={onNavigateToMessages}
          worker={selectedWorker}
          briefingItems={items}
          documentRequests={documentRequestsByWorker[selectedWorker.id] ?? []}
        />
      ) : null}
    </div>
  );
}

const DOC_CODE_TO_KO: Record<string, string> = {
  work_permit: "고용허가서 사본",
  alien_registration: "외국인등록증 사본",
  employment_contract: "표준근로계약서",
  labor_contract: "표준근로계약서",
  passport_copy: "여권 사본",
  passport: "여권 사본",
  health_certificate: "건강검진 결과서",
  criminal_record: "범죄경력 조회서",
  standard_contract: "표준근로계약서",
};

const CORE_DOCUMENT_CODES = ["passport_copy", "alien_registration", "employment_contract", "work_permit"];

const DOC_KO_TO_CODE: Record<string, string> = {
  "고용허가서 사본": "work_permit",
  고용허가서: "work_permit",
  "외국인등록증 사본": "alien_registration",
  외국인등록증: "alien_registration",
  표준근로계약서: "employment_contract",
  근로계약서: "employment_contract",
  "여권 사본": "passport_copy",
  여권: "passport_copy",
};

function docCodeToKo(code: string): string {
  return DOC_CODE_TO_KO[code.toLowerCase()] ?? code;
}

function displaySummaryText(value?: string | null): string | undefined {
  if (!value) return undefined;
  return value.replace(/\b(passport_copy|passport|alien_registration|employment_contract|labor_contract|standard_contract|work_permit|health_certificate|criminal_record)\b/g, (code) => docCodeToKo(normalizeDocCode(code)));
}

function normalizeDocCode(value: string): string {
  const trimmed = value.trim();
  const normalized = DOC_KO_TO_CODE[trimmed] ?? trimmed.toLowerCase();
  if (normalized === "labor_contract" || normalized === "standard_contract") return "employment_contract";
  return normalized;
}

function formatDday(value: number | null | undefined): string | null {
  if (value == null) return null;
  return value < 0 ? `D+${Math.abs(value)}` : `D-${value}`;
}

function displayReadinessLabel(value?: string) {
  if (value === "신청 가능") return "서류 기준 준비됨";
  if (value === "신청 불가") return "서류 보완 필요";
  return value ?? "";
}

function readinessTone(value?: string): Tone {
  if (value === "신청 가능") return "green";
  if (value === "부분 준비") return "orange";
  return "red";
}

const SEVERITY_COLOR: Record<string, Tone> = {
  CRITICAL: "red",
  HIGH: "orange",
  MEDIUM: "orange",
  LOW: "gray",
};

function buildRisksFromBriefingItem(item: DailyBriefingItem) {
  const risks: Array<{ title: string; desc: string; severity: string; basis: string[] }> = [];
  const basis = item.source_labels.length > 0 ? item.source_labels : ["근로자 프로필", "체류 정보"];

  if (item.risk_type === "visa_expiry") {
    const label = item.expired
      ? `체류기간 초과 ${item.days_overdue ?? 0}일`
      : `체류만료 D-${item.d_day}`;
    risks.push({
      title: item.expired ? "체류기간 초과" : "체류만료 임박",
      desc: displaySummaryText(item.case_summary) ?? label,
      severity: item.severity,
      basis,
    });
  } else if (item.risk_type === "contract_visa_conflict") {
    risks.push({
      title: "계약·체류 충돌",
      desc: displaySummaryText(item.case_summary) ?? "계약종료일이 비자만료일보다 늦습니다. 체류 연장 또는 계약 조정이 필요합니다.",
      severity: item.severity,
      basis,
    });
  } else if (item.risk_type === "missing_document") {
    const docs = item.missing_documents.length > 0
      ? item.missing_documents.map(docCodeToKo).join(", ")
      : "서류 확인 필요";
    risks.push({
      title: "서류 보완 필요",
      desc: displaySummaryText(item.case_summary) ?? `누락 서류: ${docs}`,
      severity: item.severity,
      basis,
    });
  } else if (item.risk_type === "reporting_deadline") {
    risks.push({
      title: "고용변동 신고 기한",
      desc: displaySummaryText(item.case_summary) ?? `신고 기한이 임박했습니다 (D-${item.d_day}).`,
      severity: item.severity,
      basis,
    });
  } else {
    risks.push({
      title: item.case_title ?? "확인 필요",
      desc: displaySummaryText(item.case_summary) ?? "담당자가 확인해야 합니다.",
      severity: item.severity,
      basis,
    });
  }
  return risks;
}

function AgentPrepSummary({
  result,
  onSendToWorker,
  onSendToScrivener,
  sending,
  createdCount,
  onGoToMessages,
}: {
  result: AgentReviewResult;
  onSendToWorker?: () => void;
  onSendToScrivener?: () => void;
  sending?: "worker" | "scrivener" | null;
  createdCount?: number;
  onGoToMessages?: () => void;
}) {
  const s = result.summary_structured;
  const hasDocSection = (s.present_docs && s.present_docs.length > 0) || (s.missing_critical && s.missing_critical.length > 0) || (s.missing_supplementary && s.missing_supplementary.length > 0);
  return (
    <div className={styles.agentSummaryFull}>
      {s.action_plan && s.action_plan.length > 0 && (
        <div className={styles.agentSection}>
          <div className={styles.agentSectionTitle}>지금 해야 할 일</div>
          {s.action_plan.map((item, i) => (
            <div className={styles.agentActionItem} key={i}>
              <span className={styles.agentActionIndex}>{i + 1}</span>
              {item}
            </div>
          ))}
        </div>
      )}
      {hasDocSection && (
        <div className={styles.agentSection}>
          <div className={styles.agentSectionTitle}>서류 현황</div>
          {s.present_docs?.map((doc) => (
            <div className={styles.agentDocPresent} key={doc}>
              <Badge tone="green">확보됨</Badge> {doc}
            </div>
          ))}
          {s.missing_critical?.map((doc) => (
            <div className={styles.agentDocMissing} key={doc}>
              <Badge tone="red">필수 누락</Badge> {doc}
            </div>
          ))}
          {s.missing_supplementary?.map((doc) => (
            <div className={styles.agentDocMissing} key={doc}>
              <Badge tone="orange">보완</Badge> {doc}
            </div>
          ))}
          {s.submission_readiness && (
            <div style={{ marginTop: 6 }}>
              <Badge tone={readinessTone(s.submission_readiness)}>{displayReadinessLabel(s.submission_readiness)}</Badge>
            </div>
          )}
        </div>
      )}
      {s.handoff_triggered && (
        <div className={styles.agentHandoffAlert}>행정사 검토 패키지 준비됨</div>
      )}
      {result.risk_flags.length > 0 && (
        <details className={styles.agentDetails}>
          <summary>분석 상세 ({result.risk_flags.length}개 플래그)</summary>
          {result.risk_flags.map((flag, i) => (
            <div className={styles.agentFlagItem} key={i}>{flag}</div>
          ))}
        </details>
      )}

      {/* 초안 생성 완료 배너 */}
      {createdCount != null && createdCount > 0 && onGoToMessages && (
        <button
          type="button"
          className={styles.agentDraftBanner}
          onClick={onGoToMessages}
        >
          {createdCount}건 초안 생성됨 → 메시지 관리에서 검토하기
        </button>
      )}

      {/* 메시지 생성 버튼 */}
      {((s.missing_critical && s.missing_critical.length > 0) || s.handoff_triggered) && (
        <div className={styles.agentSection}>
          <div className={styles.agentSectionTitle}>메시지 보내기</div>
          {s.missing_critical && s.missing_critical.length > 0 && onSendToWorker && (
            <button
              type="button"
              className={styles.agentMsgButton}
              disabled={sending === "worker"}
              onClick={onSendToWorker}
            >
              {sending === "worker" ? "생성 중…" : "근로자에게 서류 요청 메시지 만들기"}
            </button>
          )}
          {s.handoff_triggered && onSendToScrivener && (
            <button
              type="button"
              className={cn(styles.agentMsgButton, styles.agentMsgButtonScrivener)}
              disabled={sending === "scrivener"}
              onClick={onSendToScrivener}
            >
              {sending === "scrivener" ? "생성 중…" : "행정사에게 검토 패키지 메시지 만들기"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function TodayWorkerDetail({
  onAction,
  onClose,
  onNavigateToMessages,
  worker,
  briefingItems,
  documentRequests,
}: {
  onAction?: (action: PcViewAction) => void;
  onClose: () => void;
  onNavigateToMessages?: (threadId: string, tab?: "worker" | "expert") => void;
  worker: (typeof workers)[number];
  briefingItems?: DailyBriefingItem[];
  documentRequests?: WorkerDocumentRequest[];
}) {
  const workerBriefingItems = useMemo(() => {
    const matched = (briefingItems ?? []).filter((i) => i.subject_id === worker.id);
    return [...matched].sort((a, b) => {
      const statusDelta = (statusPriority[severityLabel(b)] ?? 0) - (statusPriority[severityLabel(a)] ?? 0);
      if (statusDelta !== 0) return statusDelta;
      return (b.primary_action?.approval_required ? 1 : 0) - (a.primary_action?.approval_required ? 1 : 0);
    });
  }, [briefingItems, worker.id]);
  const workerBriefingItem = workerBriefingItems[0] ?? null;
  const [agentResult, setAgentResult] = useState<AgentReviewResult | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [msgSending, setMsgSending] = useState<"worker" | "scrivener" | null>(null);
  const [createdThreadIds, setCreatedThreadIds] = useState<string[]>([]);
  const [lastCreatedThreadId, setLastCreatedThreadId] = useState<string | null>(null);
  const [lastCreatedChannel, setLastCreatedChannel] = useState<"worker" | "expert">("worker");
  const [submittedDocTypes, setSubmittedDocTypes] = useState<Set<string> | null>(null);
  const [preAgentDocStatus, setPreAgentDocStatus] = useState<{
    present: string[];
    missingCritical: string[];
    missingSupplementary: string[];
  } | null>(null);

  useEffect(() => {
    setAgentResult(null);
    setAgentLoading(false);
    setCreatedThreadIds([]);
    setLastCreatedThreadId(null);
    setPreAgentDocStatus(null);
  }, [worker.id]);

  const realWorkerId = workerBriefingItem?.subject_id ?? worker.id;
  const companyId = "550e8400-e29b-41d4-a716-446655440001";
  const actionId = workerBriefingItem?.primary_action?.action_id ?? null;
  const analysisSignature = useMemo(() => {
    const briefingSignature = workerBriefingItems.map((item) => ({
      item_id: item.item_id,
      risk_type: item.risk_type,
      severity: item.severity,
      d_day: item.d_day,
      expired: item.expired,
      days_overdue: item.days_overdue,
      missing_documents: [...item.missing_documents].sort(),
      action_id: item.primary_action?.action_id ?? null,
      action_status: item.primary_action?.status ?? null,
      approved_at: item.primary_action?.approved_at ?? null,
    }));
    const documentSignature = [...(documentRequests ?? [])]
      .map((request) => ({
        doc_type: normalizeDocCode(request.doc_type),
        status: request.status ?? "",
      }))
      .sort((a, b) => a.doc_type.localeCompare(b.doc_type));
    return JSON.stringify({ workerId: worker.id, briefing: briefingSignature, documents: documentSignature });
  }, [documentRequests, worker.id, workerBriefingItems]);
  const cacheKey = actionId ? `${worker.id}:${actionId}:${analysisSignature}` : null;

  useEffect(() => {
    setAgentResult(null);
    setAgentLoading(false);
    setMsgSending(null);
    setCreatedThreadIds([]);
    setLastCreatedThreadId(null);
  }, [worker.id, actionId, analysisSignature]);

  useEffect(() => {
    async function loadWorkerDocs() {
      try {
        const res = await fetch(`/api/v1/documents/worker-doc-status?worker_id=${realWorkerId}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        setPreAgentDocStatus({
          present: data.present ?? [],
          missingCritical: data.missing_critical ?? [],
          missingSupplementary: data.missing_supplementary ?? [],
        });
      } catch {
        setPreAgentDocStatus({ present: [], missingCritical: [], missingSupplementary: [] });
      }
    }
    void loadWorkerDocs();
  }, [realWorkerId]);

  async function handleRunAnalysis() {
    if (!actionId || !cacheKey) return;
    const cached = agentReviewCache.get(cacheKey);
    if (cached) {
      setAgentResult(cached);
      return;
    }
    setAgentLoading(true);
    setCreatedThreadIds([]);
    setLastCreatedThreadId(null);
    try {
      const result = await runAgentReview(actionId);
      agentReviewCache.set(cacheKey, result);
      setAgentResult(result);
    } finally {
      setAgentLoading(false);
    }
  }

  async function handleSendToWorker() {
    const actionId = workerBriefingItem?.primary_action?.action_id;
    if (!actionId || !agentResult) return;
    setMsgSending("worker");
    try {
      const s = agentResult.summary_structured;
      const missingDocs = s.missing_critical ?? [];
      const dDay = formatDday(s.visa_d_day);
      const contextLines = [
        "누락 서류 목록:",
        ...missingDocs.map((doc) => `- ${doc} (필수)`),
        dDay ? `\n제출 기한: ${dDay} 이내` : null,
        "\n참고: 서류 제출 후 담당자가 확인 연락드립니다.",
      ].filter(Boolean).join("\n");
      const extraContext = missingDocs.length > 0 ? contextLines : undefined;
      const thread = await createMessageDraftForAction({
        workerId: realWorkerId,
        companyId,
        messagePurpose: "missing_document_request",
        sourceActionId: actionId,
        extraContext,
      });
      setCreatedThreadIds((prev) => [...prev, thread.id]);
      setLastCreatedThreadId(thread.id);
      setLastCreatedChannel("worker");
    } finally {
      setMsgSending(null);
    }
  }

  async function handleSendToScrivener() {
    if (!actionId || !agentResult) return;
    setMsgSending("scrivener");
    try {
      const s = agentResult.summary_structured;
      const lines = [
        "■ 상황 요약",
        s.visa_d_day != null ? `- 체류 만료: ${formatDday(s.visa_d_day)}` : null,
        s.visa_risk ? `- 위험도: ${s.visa_risk}` : null,
        s.missing_critical?.length ? "\n■ 필수 누락 서류" : null,
        ...(s.missing_critical?.map((d) => `- ${d} (필수)`) ?? []),
        s.missing_supplementary?.length ? "\n■ 선택 누락 서류" : null,
        ...(s.missing_supplementary?.map((d) => `- ${d}`) ?? []),
        s.present_docs?.length ? "\n■ 보유 확인 서류" : null,
        ...(s.present_docs?.map((d) => `- ${d} ✓`) ?? []),
        `\n■ 서류 기준 상태: ${displayReadinessLabel(s.submission_readiness)}`,
        "\n■ 요청 사항",
        "위 내용 확인 후 체류 연장 신청 검토 및 서류 준비를 도와주시기 바랍니다.",
      ].filter(Boolean).join("\n");
      const thread = await createMessageDraftForAction({
        workerId: realWorkerId,
        companyId,
        messagePurpose: "handoff_notification",
        sourceActionId: actionId,
        extraContext: lines,
      });
      setCreatedThreadIds((prev) => [...prev, thread.id]);
      setLastCreatedThreadId(thread.id);
      setLastCreatedChannel("expert");
    } finally {
      setMsgSending(null);
    }
  }

  function handleGoToMessages() {
    if (lastCreatedThreadId) {
      onNavigateToMessages?.(lastCreatedThreadId, lastCreatedChannel);
    }
  }

  const risks = workerBriefingItems.length > 0
    ? workerBriefingItems.flatMap(buildRisksFromBriefingItem).slice(0, 4)
    : [{ title: "확인 필요", desc: "계약·체류·서류 상태를 담당자가 확인해야 합니다.", severity: "MEDIUM", basis: ["근로자 프로필"] }];

  const missingSet = new Set(workerBriefingItems.flatMap((item) => item.missing_documents.map(normalizeDocCode)));
  const preMissingSet = new Set([
    ...(preAgentDocStatus?.missingCritical ?? []),
    ...(preAgentDocStatus?.missingSupplementary ?? []),
  ].map(normalizeDocCode));
  const prePresentSet = new Set((preAgentDocStatus?.present ?? []).map(normalizeDocCode));
  const agentMissingSet = new Set([
    ...(agentResult?.summary_structured?.missing_critical ?? []),
    ...(agentResult?.summary_structured?.missing_supplementary ?? []),
  ].map(normalizeDocCode));
  const agentPresentSet = new Set((agentResult?.summary_structured?.present_docs ?? []).map(normalizeDocCode));
  const requestStatusByDoc = new Map((documentRequests ?? []).map((request) => [normalizeDocCode(request.doc_type), request.status ?? ""]));
  const hasAgentAnalysis = Boolean(agentResult);
  const hasAnyDocumentSignal = workerBriefingItems.some((item) => item.risk_type === "missing_document" || item.missing_documents.length > 0)
    || preMissingSet.size > 0
    || prePresentSet.size > 0
    || agentMissingSet.size > 0
    || agentPresentSet.size > 0
    || requestStatusByDoc.size > 0;

  const docs: Array<[string, string, Tone]> = CORE_DOCUMENT_CODES.map((code) => {
    if (agentMissingSet.has(code) || missingSet.has(code) || preMissingSet.has(code)) return [docCodeToKo(code), "보완 필요", "orange" as Tone];
    if (agentPresentSet.has(code) || prePresentSet.has(code)) return [docCodeToKo(code), "확보됨", "green" as Tone];
    const requestStatus = requestStatusByDoc.get(code);
    if (requestStatus === "ACCEPTED") return [docCodeToKo(code), "확인 완료", "green" as Tone];
    if (requestStatus === "SUBMITTED") return [docCodeToKo(code), "담당자 확인 전", "orange" as Tone];
    if (!hasAnyDocumentSignal) return [docCodeToKo(code), hasAgentAnalysis ? "자료 없음" : "분석 후 확인", "gray" as Tone];
    return [docCodeToKo(code), "확인 필요", "gray" as Tone];
  });
  const hasMissingDocs = agentMissingSet.size > 0 || missingSet.size > 0;
  const shouldHandoff = Boolean(agentResult?.summary_structured?.handoff_triggered || workerBriefingItem?.primary_action?.action_type === "create_handoff");
  const visaDeadline = workerBriefingItem ? deadlineLabel(workerBriefingItem) : worker.dday;
  const recommendedAction = hasMissingDocs
    ? {
      title: "근로자에게 서류 보완 요청",
      desc: "누락된 필수 서류를 먼저 요청하고 제출 상태를 확인합니다.",
      label: "요청 초안 보기",
      kind: "document-draft" as PcActionKind,
    }
    : shouldHandoff
      ? {
        title: "행정사 검토 자료 만들기",
        desc: "체류 만료와 계약 정보를 묶어 행정사에게 전달할 검토 패키지를 확인합니다.",
        label: "검토 자료 보기",
        kind: "handoff-preview" as PcActionKind,
      }
      : {
        title: "상태 재확인",
        desc: "현재 데이터가 부족하거나 낮은 우선순위 케이스입니다. 최신 서류 상태를 먼저 확인합니다.",
        label: "상태 보기",
        kind: "handoff-preview" as PcActionKind,
      };

  return (
    <aside className={styles.todayDetail} data-testid="dashboard-detail-panel">
      <div className={styles.pageHead}>
        <div className={styles.subtle}>근로자 상세</div>
        <button className={styles.closeButton} data-testid="dashboard-detail-close" onClick={onClose} type="button" aria-label="상세 패널 닫기">×</button>
      </div>

      <div className={styles.detailHeader}>
        <span className={styles.bigAvatar}>{worker.initials}</span>
        <div>
          <h2>{worker.name}</h2>
          <p className={styles.subtle}>{worker.nationalityCode} {worker.nationality} · {worker.visaType} · 근속 {worker.tenure}</p>
          <p className={styles.subtle}>{worker.line} · 외등록 950***-5******</p>
        </div>
      </div>

      {/* 왜 확인이 필요한가요? */}
      <div className={styles.reasonBox}>
        <div className={styles.reasonBoxTitle}>
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6.5" stroke="#1D4ED8" strokeWidth="1.4"/>
            <path d="M8 7v4M8 5.5h.01" stroke="#1D4ED8" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
          왜 확인이 필요한가요?
        </div>
        {risks.slice(0, 2).map((r, index) => (
          <div className={styles.reasonItem} key={`${r.title}-${index}`}>
            <span className={styles.reasonDot} />
            <span><strong>{r.title}</strong> — {r.desc}</span>
          </div>
        ))}
      </div>

      {/* AI가 준비한 일 */}
      <section className={styles.detailSection}>
        <div className={styles.sectionLabelUpper}>
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
            <path d="M8 1l1.5 4.5H14l-3.75 2.75L11.5 13 8 10.25 4.5 13l1.25-4.75L2 5.5h4.5L8 1z" stroke="#1B3FA0" strokeWidth="1.3" strokeLinejoin="round"/>
          </svg>
          AI가 준비한 일
        </div>
        {agentResult ? (
          <AgentPrepSummary
            result={agentResult}
            onSendToWorker={handleSendToWorker}
            onSendToScrivener={handleSendToScrivener}
            sending={msgSending}
            createdCount={createdThreadIds.length}
            onGoToMessages={handleGoToMessages}
          />
        ) : (
          <button
            type="button"
            className={styles.agentRunButton}
            disabled={agentLoading || !actionId}
            onClick={handleRunAnalysis}
          >
            {agentLoading ? "분석 중…" : "에이전트 분석 실행"}
          </button>
        )}
      </section>

      <section className={styles.detailSection}>
        <h3>현재 리스크 <Badge tone="gray">{risks.length}</Badge></h3>
        <div className={styles.stack}>
          {risks.map((risk, index) => (
            <Card className={styles.riskCard} key={`${risk.title}-${index}`}>
              <div className={styles.sectionTitle}>
                <strong>{risk.title}</strong>
                <Badge tone={SEVERITY_COLOR[risk.severity] ?? "gray"}>{risk.severity}</Badge>
              </div>
              <p>{risk.desc}</p>
              <div className={styles.buttonRow}>
                {risk.basis.map((basis, index) => <Badge key={basis} tone={index === 0 ? "blue" : "gray"}>{basis}</Badge>)}
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>체류 / 계약</h3>
        <div className={styles.infoGrid}>
          <Card className={styles.panel}><div className={styles.subtle}>체류만료일</div><strong>{worker.visaExpiry}</strong><div className={styles.textOrange}>{visaDeadline}</div></Card>
          <Card className={styles.panel}><div className={styles.subtle}>계약종료일</div><strong>{worker.contractEnd}</strong><div className={styles.subtle}>계약 기준</div></Card>
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>제출 서류 {docs.length > 0 && <Badge tone="gray">{docs.length}</Badge>}</h3>
        <div className={styles.stack}>
          {docs.map(([name, status, tone], i) => (
            <div className={cn(styles.docRow, styles.panel)} key={`${i}-${name}`}>
              <span><FileText size={16} /> {name}</span>
              <Badge tone={tone}>{status}</Badge>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>추천 액션 <Badge tone="gray">1</Badge></h3>
        <div className={styles.stack}>
          <Card className={styles.actionCard}>
            <div>
              <strong>{recommendedAction.title}</strong>
              <p className={styles.subtle}>{recommendedAction.desc}</p>
            </div>
            <Button data-testid="action-handoff" variant="secondary" onClick={() => onAction?.({ kind: recommendedAction.kind, label: recommendedAction.label, subjectId: worker.id, subjectName: worker.name, riskType: workerBriefingItem?.risk_type ?? null })}>{recommendedAction.label}</Button>
          </Card>
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>근거 자료 <Badge tone="gray">{workerBriefingItem?.citation_ids.length || 3}</Badge></h3>
        <div className={styles.stack}>
          {workerBriefingItem?.citation_ids.length ? (
            workerBriefingItem.citation_ids.map((citationId) => (
              <Evidence key={citationId} source="브리핑 근거" text={citationId} grade="B" />
            ))
          ) : (
            <>
              <Evidence source="국가법령정보센터" text="출입국관리법 제25조 (체류기간 연장허가)" grade="A" />
              <Evidence source="HiKorea" text="체류기간 연장허가 신청 안내" grade="B" />
              <Evidence source="EPS 고용허가제" text="외국인근로자 고용 시 보유 서류" grade="B" />
            </>
          )}
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>업무 기록</h3>
        <div className={styles.timeline}>
          {workerBriefingItems.length > 0 ? (
            workerBriefingItems.slice(0, 4).map((item, index) => (
              <div className={styles.row} key={item.item_id}>
                <span className={cn(styles.dot, index === 0 ? styles.toneBlue : styles.toneGray)} />
                <div>
                  <strong>{item.case_title ?? "리스크 플래그"}</strong>
                  <div className={styles.subtle}>{deadlineLabel(item)} · 오늘 브리핑</div>
                </div>
              </div>
            ))
          ) : (
            <div className={styles.subtle}>아직 표시할 업무 기록이 없습니다.</div>
          )}
        </div>
      </section>
    </aside>
  );
}

function Scenario({ title, desc, tone }: { title: string; desc: string; tone: Tone }) {
  return <div className={cn(styles.panel, toneClass(tone))}><strong>{title}</strong><p>{desc}</p></div>;
}

function InfoTable({ title, rows }: { title: string; rows: string[][] }) {
  return (
    <section>
      <h2>{title}</h2>
      <div className={styles.infoTable}>{rows.map(([key, value]) => <div className={styles.infoRow} key={key}><span className={styles.subtle}>{key}</span><strong>{value}</strong></div>)}</div>
    </section>
  );
}

function Evidence({ source, text, grade }: { source: string; text: string; grade: string }) {
  return <div className={cn(styles.panel, styles.toneGray)}><div className={styles.badgeLine}><Badge>{grade}</Badge><span className={styles.subtle}>{source}</span></div><strong>{text}</strong></div>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><div className={styles.subtle}>{label}</div><strong>{value}</strong></div>;
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h3 className={styles.titleLine}><CheckCircle size={16} /> {title}</h3>{children}</section>;
}

function Timeline() {
  const items = ["체류만료일 확인", "누락 서류 감지", "이전 대화 기록 확인", "베트남어 메시지 초안 생성", "대표 승인 요청", "발송 예정 상태로 제한 적용"];
  return <div className={styles.timeline}>{items.map((item, index) => <div className={styles.row} key={item}><span className={cn(styles.dot, styles.toneGreen)} /><div><strong>{item}</strong><div className={styles.subtle}>2026-05-21 10:{10 + index * 3}</div></div></div>)}</div>;
}

