import {
  Check,
  CheckCircle,
  Download,
  FileText,
  MessageSquare,
  MoreHorizontal,
  RefreshCcw,
  Search,
  UserRoundPlus,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import { getCaseAuditReview } from "../../../lib/api";
import type { CaseAuditReview, DailyBriefingItem, DailyBriefingResult, EvidenceEvent } from "../../../types/dailyBriefing";
import { adminPackage, contactItems, judgmentRows, riskCases, todaysTasks, workers, type Tone } from "../data";
import { Badge, Button, Card, cn, PillButton, textToneClass, toneClass } from "../ui";
import styles from "../PcShell.module.css";

const summary = [
  {
    id: "visa", label: "체류기간 임박", count: 4, unit: "명",
    color: "#EF4444", bg: "#FEF2F2", workerId: "w_bayar",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="#EF4444" strokeWidth="1.8"/><path d="M12 7v5l3 3" stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "docs", label: "서류 보완 필요", count: 7, unit: "건",
    color: "#F97316", bg: "#FFF7ED", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="#F97316" strokeWidth="1.8" strokeLinejoin="round"/><path d="M14 2v6h6M12 12v4M12 10h.01" stroke="#F97316" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "recruit", label: "신규 채용 준비", count: 1, unit: "건",
    color: "#10B981", bg: "#ECFDF5", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3.5" stroke="#10B981" strokeWidth="1.8"/><path d="M3 20c0-3.866 2.686-6 6-6s6 2.134 6 6" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round"/><path d="M17 6l1.5 1.5L21 5" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>),
  },
  {
    id: "contact", label: "컨택 대기", count: 4, unit: "건",
    color: "#8B5CF6", bg: "#F5F3FF", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M4 4h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H6l-4 4V5a1 1 0 0 1 1-1z" stroke="#8B5CF6" strokeWidth="1.8" strokeLinejoin="round"/></svg>),
  },
  {
    id: "reply", label: "응답 도착", count: 2, unit: "건",
    color: "#0EA5E9", bg: "#F0F9FF", workerId: "w_tran",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="#0EA5E9" strokeWidth="1.8" strokeLinejoin="round"/><path d="M8 10h8M8 14h4" stroke="#0EA5E9" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "approval", label: "승인 대기", count: 5, unit: "건",
    color: "#F59E0B", bg: "#FFFBEB", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="#F59E0B" strokeWidth="1.8" strokeLinejoin="round"/></svg>),
  },
  {
    id: "handoff", label: "행정사 검토 준비", count: 2, unit: "건",
    color: "#6366F1", bg: "#EEF2FF", workerId: "w_bayar",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M9 11l3 3L22 4" stroke="#6366F1" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#6366F1" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
];
const totalRiskCaseCount = riskCases.length;

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
};

export type PcViewProps = {
  onAction?: (action: PcViewAction) => void;
};

type JudgmentLogViewProps = PcViewProps & {
  briefing?: DailyBriefingResult | null;
};

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

function judgmentStatus(item: DailyBriefingItem) {
  if (item.primary_action?.status === "pending_approval") return "승인 대기";
  if (item.primary_action?.status === "approved") return "승인 완료";
  if (item.primary_action?.status === "revision_requested") return "수정 요청";
  if (item.primary_action?.action_type === "create_handoff") return "행정사 검토";
  return "담당자 확인";
}

function rowsFromBriefing(briefing?: DailyBriefingResult | null) {
  const grouped = new Map<string, DailyBriefingItem[]>();
  for (const item of briefing?.items ?? []) {
    const key = item.subject_type === "worker" ? item.subject_id : item.case_id || item.item_id;
    grouped.set(key, [...(grouped.get(key) ?? []), item]);
  }
  const statusPriority: Record<string, number> = {
    "승인 대기": 5,
    "수정 요청": 4,
    "행정사 검토": 3,
    "담당자 확인": 2,
    "승인 완료": 1,
  };
  return [...grouped.entries()].map(([key, items], index) => {
    const statuses = [...new Set(items.map(judgmentStatus))].sort((a, b) => (statusPriority[b] ?? 0) - (statusPriority[a] ?? 0));
    const titles = [...new Set(items.map((item) => item.case_title ?? item.risk_type))];
    const summaries = items.map((item) => item.case_summary ?? item.case_title ?? item.risk_type);
    const primary = items[0];
    return {
      id: key,
      displayId: `#${String(index + 1).padStart(3, "0")}`,
      items,
      caseIds: [...new Set(items.map((item) => item.case_id).filter(Boolean))],
      citationIds: [...new Set(items.flatMap((item) => item.citation_ids ?? []))],
      sourceLabels: [...new Set(items.flatMap((item) => item.source_labels ?? []))],
      worker: primary.subject_display_name ?? primary.subject_display_id ?? primary.subject_id,
      status: statuses[0] ?? "담당자 확인",
      date: briefing?.date ?? "-",
      title: titles.length > 1 ? `${titles[0]} 외 ${titles.length - 1}건` : titles[0],
      summary: summaries.join("\n"),
      caseCount: items.length,
    };
  });
}

type ApprovalHistoryRow = Record<string, unknown>;

const APPROVAL_STATUS_LABELS: Record<string, { label: string; bg: string; fg: string }> = {
  pending: { label: "승인 대기", bg: "rgba(255,146,0,0.10)", fg: "#9C5800" },
  pending_approval: { label: "승인 대기", bg: "rgba(255,146,0,0.10)", fg: "#9C5800" },
  approved: { label: "승인 완료", bg: "rgba(0,191,64,0.10)", fg: "#006E25" },
  rejected: { label: "반려", bg: "rgba(255,66,66,0.10)", fg: "#B00C0C" },
  revision_requested: { label: "수정 요청", bg: "rgba(255,146,0,0.10)", fg: "#9C5800" },
};

const EVENT_LABELS: Record<string, string> = {
  input_received: "요청 수신",
  state_loaded: "상태 로드",
  risk_flagged: "리스크 감지",
  rag_retrieved: "근거 검색",
  approval_requested: "승인 요청",
  approval_approved: "승인 완료",
  approval_rejected: "반려",
  approval_revision_requested: "수정 요청",
  tool_executed: "도구 실행",
  final_response_generated: "응답 생성",
};

function compactId(value: string | null | undefined) {
  if (!value) return "";
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-4)}` : value;
}

function textValue(row: ApprovalHistoryRow, key: string) {
  const value = row[key];
  return typeof value === "string" ? value : "";
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function actionLabel(actionType: string | null | undefined) {
  if (actionType === "request_document") return "누락서류 요청 초안";
  if (actionType === "create_handoff") return "행정사 검토 자료";
  return "승인 대상 작업";
}

export function JudgmentLogView({ onAction, briefing }: JudgmentLogViewProps = {}) {
  const rows = rowsFromBriefing(briefing);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [auditByCaseId, setAuditByCaseId] = useState<Record<string, CaseAuditReview>>({});
  const [auditLoading, setAuditLoading] = useState(false);

  const statusStyle: Record<string, { bg: string; fg: string }> = {
    "승인 완료":    { bg: "rgba(0,191,64,0.10)",  fg: "#006E25" },
    "발송 예정":    { bg: "rgba(0,102,255,0.07)", fg: "#003699" },
    "수정 요청":    { bg: "rgba(255,146,0,0.10)", fg: "#9C5800" },
    "담당자 확인":  { bg: "rgba(0,102,255,0.07)", fg: "#003699" },
    "승인 대기":    { bg: "rgba(255,146,0,0.10)", fg: "#9C5800" },
    "검토 자료 준비": { bg: "rgba(112,115,124,0.08)", fg: "#70737C" },
  };

  const selected = rows.find((r) => r.id === selectedId) ?? rows[0] ?? null;
  const selectedCaseKey = selected?.caseIds.join("|") ?? "";

  useEffect(() => {
    if (!selected?.caseIds.length) return;
    const missingCaseIds = selected.caseIds.filter((caseId) => !auditByCaseId[caseId]);
    if (!missingCaseIds.length) return;

    let cancelled = false;
    setAuditLoading(true);
    Promise.all(
      missingCaseIds.map(async (caseId) => {
        try {
          return await getCaseAuditReview(caseId);
        } catch {
          return null;
        }
      }),
    ).then((reviews) => {
      if (cancelled) return;
      setAuditByCaseId((prev) => {
        const next = { ...prev };
        for (const review of reviews) {
          if (review) next[review.case.case_id] = review;
        }
        return next;
      });
    }).finally(() => {
      if (!cancelled) setAuditLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [selectedCaseKey]);

  const selectedAudits = useMemo(
    () => (selected?.caseIds ?? []).map((caseId) => auditByCaseId[caseId]).filter((review): review is CaseAuditReview => Boolean(review)),
    [auditByCaseId, selectedCaseKey],
  );

  const approvalRows = useMemo(() => {
    const rowsFromAudit = selectedAudits.flatMap((audit) =>
      audit.approval_history.map((approval) => ({
        approval,
        action: audit.actions.find((action) => action.action_id === textValue(approval, "action_id")),
        caseRiskType: audit.case.risk_type,
      })),
    );
    if (rowsFromAudit.length) return rowsFromAudit;
    return (selected?.items ?? [])
      .map((item) => item.primary_action)
      .filter(Boolean)
      .map((action) => ({
        approval: {
          approval_id: action!.approval_id,
          action_id: action!.action_id,
          status: action!.status,
          updated_at: action!.approved_at,
          created_at: null,
        },
        action,
        caseRiskType: action!.action_type,
      }));
  }, [selectedAudits, selected?.items]);

  const timelineEvents = useMemo(() => {
    const eventMap = new Map<string, EvidenceEvent>();
    for (const event of selectedAudits.flatMap((audit) => audit.evidence_events)) {
      eventMap.set(event.event_id, event);
    }
    return [...eventMap.values()].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  }, [selectedAudits]);

  const infoTags = useMemo(() => {
    const citationTitles = selectedAudits.flatMap((audit) => audit.citation_details.map((citation) => citation.title));
    const tags = [
      ...(selected?.sourceLabels ?? []),
      ...citationTitles,
      ...(selected?.citationIds ?? []).map((id) => compactId(id)),
    ].filter(Boolean);
    return [...new Set(tags)].slice(0, 8);
  }, [selected?.sourceLabels, selected?.citationIds, selectedAudits]);

  return (
    <div className={styles.judgmentLayout}>

      {/* 왼쪽 — 목록 */}
      <section className={styles.judgmentList}>
        <div className={styles.pageHead} style={{ marginBottom: 12 }}>
          <h1 className={styles.headline} style={{ fontSize: 20 }}>판단 기록</h1>
        </div>

        {/* 필터 Chip 바 */}
        <div className={styles.buttonRow} style={{ marginBottom: 8 }}>
          <button className={cn(styles.chip, styles.chipActive)} type="button">전체</button>
          <button className={styles.chip} type="button">승인 대기 <span className={styles.chipCount}>{rows.filter((row) => row.status === "승인 대기").length}</span></button>
          <button className={styles.chip} type="button">담당자 확인 <span className={styles.chipCount}>{rows.filter((row) => row.status === "담당자 확인").length}</span></button>
          <button className={styles.chip} type="button">행정사 검토 <span className={styles.chipCount}>{rows.filter((row) => row.status === "행정사 검토").length}</span></button>
        </div>

        {/* 검색 바 */}
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "8px 12px", borderRadius: 9,
          border: "1px solid rgba(112,115,124,0.20)", background: "#fff", marginBottom: 14,
        }}>
          <Search size={14} color="#70737C" />
          <span style={{ fontSize: 13, color: "#B0B3BA" }}>키워드 검색 (사유, 이벤트, 대상 등)</span>
        </div>

        {/* 그리드 테이블 */}
        <div className={styles.workerGrid}>
          {/* 헤더 */}
          <div style={{
            display: "grid", gridTemplateColumns: "24px 64px minmax(130px, 1fr) 96px 84px",
            padding: "9px 14px", gap: 10,
            fontSize: 11.5, fontWeight: 600, color: "#70737C",
            borderBottom: "1px solid rgba(112,115,124,0.12)", background: "#fafafa",
          }}>
            <div><input type="checkbox" aria-label="전체 선택" /></div>
            <div>판단 기록</div>
            <div>대상 근로자</div>
            <div>최종 상태</div>
            <div>판단일</div>
          </div>

          {/* 데이터 행 */}
          {rows.map((row) => {
            const ss = statusStyle[row.status] ?? { bg: "rgba(112,115,124,0.08)", fg: "#70737C" };
            const isSelected = row.id === selectedId;
            return (
              <div
                key={row.id}
                style={{
                  display: "grid", gridTemplateColumns: "24px 64px minmax(130px, 1fr) 96px 84px",
                  padding: "11px 14px", gap: 10, alignItems: "center",
                  borderBottom: "1px solid rgba(112,115,124,0.08)",
                  background: isSelected ? "rgba(0,102,255,0.04)" : "transparent",
                  cursor: "pointer", transition: "background 0.15s",
                  borderLeft: isSelected ? "2px solid #0066FF" : "2px solid transparent",
                }}
                onClick={() => setSelectedId(row.id)}
              >
                <div><input type="checkbox" aria-label={`${row.id} 선택`} onClick={(e) => e.stopPropagation()} /></div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#1D4ED8" }}>{row.displayId}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.worker}</div>
                  <div className={styles.subtle} style={{ fontSize: 11.5, marginTop: 2 }}>{row.caseCount}건</div>
                </div>
                <div>
                  <span style={{
                    display: "inline-flex", padding: "2px 8px", borderRadius: 99,
                    fontSize: 11.5, fontWeight: 700,
                    background: ss.bg, color: ss.fg,
                    whiteSpace: "nowrap",
                  }}>{row.status}</span>
                </div>
                <div style={{ fontSize: 12, color: "#70737C" }}>{row.date}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 오른쪽 — 상세 패널 */}
      <aside className={styles.judgmentDetail}>
        {/* 헤더 */}
        <div className={styles.pageHead} style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>판단 기록 {selected?.displayId ?? "-"}</h2>
            <span style={{
              display: "inline-flex", padding: "3px 10px", borderRadius: 99,
              fontSize: 11.5, fontWeight: 700,
              background: (statusStyle[selected?.status ?? ""] ?? { bg: "rgba(112,115,124,0.08)" }).bg,
              color: (statusStyle[selected?.status ?? ""] ?? { fg: "#70737C" }).fg,
            }}>{selected?.status ?? "기록 없음"}</span>
          </div>
          <div className={styles.buttonRow}>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "response-summary", label: "판단 기록 메뉴" })}>
              <MoreHorizontal size={15} />
            </Button>
            <Button variant="ghost" onClick={() => onAction?.({ kind: "response-summary", label: "상세 닫기" })}>
              <X size={15} />
            </Button>
          </div>
        </div>

        {/* 기본 정보 그리드 */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 16 }}>
          {[["담당자", "김대리 (인사팀)"], ["대상 근로자", selected?.worker ?? "-"], ["관련 케이스", selected?.title ?? "-"]].map(([label, val]) => (
            <div key={label} style={{ padding: "10px 12px", borderRadius: 9, background: "rgba(112,115,124,0.05)", border: "1px solid rgba(112,115,124,0.10)" }}>
              <div className={styles.subtle} style={{ fontSize: 11, marginBottom: 3 }}>{label}</div>
              <strong style={{ fontSize: 13 }}>{val}</strong>
            </div>
          ))}
        </div>

        <div className={styles.separator} />

        {/* 판단 요약 */}
        <section style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <CheckCircle size={14} color="#0066FF" />
            <strong style={{ fontSize: 13, fontWeight: 700 }}>판단 요약</strong>
          </div>
          <div style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(0,102,255,0.05)", border: "1px solid rgba(0,102,255,0.15)", fontSize: 13.5, lineHeight: 1.65, color: "#374151", whiteSpace: "pre-line" }}>
            {selected?.summary ?? "현재 DB 브리핑 기준 판단 기록이 없습니다."}
          </div>
        </section>

        {/* 사용한 정보 */}
        <section style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <CheckCircle size={14} color="#0066FF" />
            <strong style={{ fontSize: 13, fontWeight: 700 }}>사용한 정보</strong>
          </div>
          <div className={styles.badgeLine}>
            {(infoTags.length ? infoTags : ["근로자 프로필", "체류 정보", "케이스 정보"]).map((tag) => (
              <span key={tag} style={{ padding: "3px 9px", borderRadius: 6, fontSize: 11.5, fontWeight: 500, background: "rgba(112,115,124,0.08)", color: "#374151" }}>{tag}</span>
            ))}
          </div>
        </section>

        {/* 승인 이력 */}
        <section style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <CheckCircle size={14} color="#0066FF" />
            <strong style={{ fontSize: 13, fontWeight: 700 }}>승인 이력</strong>
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {auditLoading && !approvalRows.length ? (
              <div className={styles.subtle} style={{ padding: "12px 14px", borderRadius: 10, background: "#fff", border: "1px solid rgba(112,115,124,0.12)" }}>승인 이력을 불러오는 중입니다.</div>
            ) : approvalRows.length ? approvalRows.map(({ approval, action, caseRiskType }) => {
              const status = textValue(approval, "status").toLowerCase();
              const statusMeta = APPROVAL_STATUS_LABELS[status] ?? { label: status || "상태 없음", bg: "rgba(112,115,124,0.08)", fg: "#70737C" };
              const reason = textValue(approval, "revision_reason") || textValue(approval, "rejection_reason");
              const approvalId = textValue(approval, "approval_id");
              return (
                <div key={approvalId || `${caseRiskType}-${textValue(approval, "action_id")}`} style={{ padding: "12px 14px", borderRadius: 10, background: "#fff", border: "1px solid rgba(112,115,124,0.12)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                    <div>
                      <strong style={{ fontSize: 13 }}>{action?.label ?? actionLabel(action?.action_type ?? caseRiskType)}</strong>
                      <p className={styles.subtle} style={{ fontSize: 12, margin: "2px 0 0" }}>
                        {textValue(approval, "approver_id") || "담당자 승인 대기"} · {formatDateTime(textValue(approval, "updated_at") || textValue(approval, "created_at"))}
                      </p>
                    </div>
                    <span style={{ padding: "3px 10px", borderRadius: 99, fontSize: 11.5, fontWeight: 700, background: statusMeta.bg, color: statusMeta.fg, whiteSpace: "nowrap" }}>{statusMeta.label}</span>
                  </div>
                  {reason && <p style={{ margin: "8px 0 0", fontSize: 12.5, lineHeight: 1.5, color: "#64748B" }}>{reason}</p>}
                </div>
              );
            }) : (
              <div className={styles.subtle} style={{ padding: "12px 14px", borderRadius: 10, background: "#fff", border: "1px solid rgba(112,115,124,0.12)" }}>이 판단에는 아직 승인 이력이 없습니다.</div>
            )}
          </div>
        </section>

        {/* 이벤트 타임라인 */}
        <section>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <CheckCircle size={14} color="#0066FF" />
            <strong style={{ fontSize: 13, fontWeight: 700 }}>이벤트 타임라인</strong>
          </div>
          <Timeline events={timelineEvents} loading={auditLoading} />
        </section>
      </aside>
    </div>
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

function Timeline({ events, loading }: { events: EvidenceEvent[]; loading: boolean }) {
  if (loading && !events.length) {
    return <div className={styles.subtle} style={{ padding: "12px 0" }}>이벤트 타임라인을 불러오는 중입니다.</div>;
  }
  if (!events.length) {
    return <div className={styles.subtle} style={{ padding: "12px 0" }}>기록된 이벤트가 없습니다.</div>;
  }
  return (
    <div className={styles.timeline}>
      {events.map((event) => (
        <div className={styles.row} key={event.event_id}>
          <span className={cn(styles.dot, styles.toneGreen)} />
          <div>
            <strong>{EVENT_LABELS[event.event_type] ?? event.event_type}</strong>
            <div className={styles.subtle}>{formatDateTime(event.created_at)} · {event.node_name}</div>
            <div style={{ fontSize: 12.5, color: "#64748B", lineHeight: 1.45 }}>{event.summary}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

