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
import React from "react";
import type { DailyBriefingItem, DailyBriefingResult } from "../../../types/dailyBriefing";
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

type CasesViewProps = PcViewProps & {
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

function severityGroup(item: DailyBriefingItem) {
  if (item.expired || item.severity === "CRITICAL") return "즉시 확인";
  if (item.severity === "HIGH") return "우선 확인";
  if (item.severity === "MEDIUM") return "확인 필요";
  return "참고";
}

function caseTone(item: DailyBriefingItem): keyof typeof CASE_SEV {
  if (item.expired || item.severity === "CRITICAL") return "red";
  if (item.severity === "HIGH") return "orange";
  if (item.severity === "MEDIUM") return "blue";
  return "gray";
}

function actionForItem(item: DailyBriefingItem): { kind: PcActionKind; label: string } {
  if (item.primary_action?.approval_required) return { kind: "approval-preview", label: "승인 요청" };
  if (item.primary_action?.action_type === "request_document" || item.risk_type === "missing_document") {
    return { kind: "document-draft", label: "메시지 초안" };
  }
  if (item.primary_action?.action_type === "create_handoff") return { kind: "handoff-preview", label: "요청서 보기" };
  if (item.risk_type === "worker_reply") return { kind: "response-summary", label: "응답 확인" };
  return { kind: "handoff-preview", label: "상세 보기" };
}

function riskTypeLabel(type: DailyBriefingItem["risk_type"]) {
  const labels: Record<DailyBriefingItem["risk_type"], string> = {
    visa_expiry: "체류기간 임박",
    missing_document: "서류 보완",
    contract_visa_conflict: "계약·체류 충돌",
    reporting_deadline: "신고기한",
    quota_review: "고용한도",
    candidate_readiness: "채용 준비",
    worker_reply: "근로자 응답",
  };
  return labels[type] ?? type;
}

export function CasesView({ onAction, briefing }: CasesViewProps = {}) {
  const items = briefing?.items ?? [];
  const groups = ["즉시 확인", "우선 확인", "확인 필요", "참고"];
  const groupedCounts = groups.reduce<Record<string, number>>((acc, group) => {
    acc[group] = items.filter((item) => severityGroup(item) === group).length;
    return acc;
  }, {});
  return (
    <div className={styles.stack}>

      {/* 헤더 */}
      <div>
        <div className={styles.subtle}>케이스 목록</div>
        <h1 className={styles.headline}>리스크 케이스 · {items.length}건</h1>
        <p className={styles.subtle}>AI는 비자 가능 여부를 확정하지 않으며, 담당자 검토용 근거와 초안만 제공합니다.</p>
      </div>

      {/* 필터 Chip 바 */}
      <div className={styles.buttonRow}>
        <button className={cn(styles.chip, styles.chipActive)} type="button">전체</button>
        {groups.map((group) => (
          <button className={styles.chip} type="button" key={group}>
            {group} <span className={styles.chipCount}>{groupedCounts[group] ?? 0}</span>
          </button>
        ))}
      </div>

      {/* 그룹별 카드 리스트 */}
      {groups.map((group) => {
        const groupItems = items.filter((item) => severityGroup(item) === group);
        if (!groupItems.length) return null;
        const sev = CASE_SEV[caseTone(groupItems[0])] ?? CASE_SEV.gray;
        return (
          <section className={styles.caseGroup} key={group}>

            {/* 그룹 헤더 */}
            <div className={styles.titleLine}>
              <span className={styles.dot} style={{ background: sev.dot, flexShrink: 0 }} />
              <strong>{group}</strong>
              <Badge tone="gray">{groupItems.length}건</Badge>
            </div>

            {/* 케이스 카드 */}
            {groupItems.map((item) => {
              const s = CASE_SEV[caseTone(item)] ?? CASE_SEV.gray;
              const action = actionForItem(item);
              const workerName = item.subject_display_name ?? item.subject_display_id ?? item.subject_id;
              return (
                <div
                  key={item.item_id}
                  className={styles.caseCard}
                  style={{
                    borderRadius: 12,
                    border: `1px solid ${s.bd}`,
                    background: s.bg,
                    borderLeft: `3px solid ${s.dot}`,
                    padding: "18px 20px 18px 18px",
                  }}
                >
                  <div className={styles.pageHead}>
                    <div style={{ flex: 1 }}>

                      {/* 배지 라인 */}
                      <div className={styles.badgeLine} style={{ marginBottom: 6 }}>
                        <span style={{
                          display: "inline-flex", alignItems: "center",
                          padding: "3px 9px", borderRadius: 99,
                          fontSize: 11.5, fontWeight: 700,
                          background: s.bg, border: `1px solid ${s.bd}`, color: s.fg,
                        }}>
                          {group}
                        </span>
                        <strong style={{ fontSize: 15, fontWeight: 700 }}>{item.case_title ?? riskTypeLabel(item.risk_type)}</strong>
                        <strong className={styles.muted}>{workerName}</strong>
                      </div>

                      {/* 설명 */}
                      <p style={{ fontSize: 13.5, color: "#374151", lineHeight: 1.6, margin: "0 0 12px" }}>
                        {item.case_summary ?? `${workerName}의 ${riskTypeLabel(item.risk_type)} 케이스입니다.`}
                      </p>

                      {/* 액션 Pill 버튼들 */}
                      <div className={styles.buttonRow}>
                        <PillButton onClick={() => onAction?.(action)}>{action.label}</PillButton>
                        {item.missing_documents.length > 0 && (
                          <Badge tone="orange">누락 {item.missing_documents.length}건</Badge>
                        )}
                      </div>
                    </div>

                    <span className={styles.subtle} style={{ flexShrink: 0 }}>{item.case_id}</span>
                  </div>
                </div>
              );
            })}
          </section>
        );
      })}
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

function Timeline() {
  const items = ["체류만료일 확인", "누락 서류 감지", "이전 대화 기록 확인", "베트남어 메시지 초안 생성", "대표 승인 요청", "발송 예정 상태로 제한 적용"];
  return <div className={styles.timeline}>{items.map((item, index) => <div className={styles.row} key={item}><span className={cn(styles.dot, styles.toneGreen)} /><div><strong>{item}</strong><div className={styles.subtle}>2026-05-21 10:{10 + index * 3}</div></div></div>)}</div>;
}

