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

type AdminReviewViewProps = PcViewProps & {
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

const DOC_LABELS: Record<string, string> = {
  passport_copy: "여권 사본",
  alien_registration: "외국인등록증 사본",
  employment_contract: "표준근로계약서",
  labor_contract: "표준근로계약서",
  standard_contract: "표준근로계약서",
  work_permit: "고용허가서 사본",
};

function docLabel(code: string) {
  return DOC_LABELS[code] ?? code;
}

function ddayLabel(item: DailyBriefingItem | null) {
  if (!item) return "-";
  if (item.expired && item.days_overdue != null) return `만료 후 ${item.days_overdue}일 경과`;
  if (item.d_day != null) return item.d_day < 0 ? `만료 후 ${Math.abs(item.d_day)}일 경과` : `D-${item.d_day}`;
  return item.risk_timing_label ?? "-";
}

export function AdminReviewView({ onAction, briefing }: AdminReviewViewProps = {}) {
  const handoffItem =
    briefing?.items.find((item) => item.primary_action?.action_type === "create_handoff")
    ?? briefing?.items.find((item) => item.risk_type === "contract_visa_conflict" || item.risk_type === "visa_expiry")
    ?? null;
  const missingItem = handoffItem
    ? briefing?.items.find((item) => item.subject_id === handoffItem.subject_id && item.risk_type === "missing_document")
    : null;
  const workerName = handoffItem?.subject_display_name ?? handoffItem?.subject_display_id ?? "검토 대상 없음";
  const dynamicPackage = handoffItem ? {
    title: `${workerName} 행정사 검토 패키지`,
    createdAt: briefing?.generated_at ? new Date(briefing.generated_at).toLocaleString("ko-KR") : "-",
    receiver: "행정사",
    status: handoffItem.primary_action?.status === "pending_approval" ? "승인 대기" : "검토 자료 준비",
    profile: [
      ["대상 근로자", workerName],
      ["케이스", handoffItem.case_title ?? "체류/계약 리스크"],
      ["위험도", handoffItem.severity],
    ],
    stay: [
      ["체류 상태", ddayLabel(handoffItem)],
      ["검토 요약", handoffItem.case_summary ?? "-"],
    ],
    docs: missingItem?.missing_documents.length
      ? missingItem.missing_documents.map((doc) => [docLabel(doc), "보완 필요"])
      : [["누락 서류", "현재 확인된 누락 없음"]],
  } : adminPackage;
  const docStatusStyle = (val: string): { color: string; bg: string } => {
    if (val.includes("확보")) return { color: "#006E25", bg: "rgba(0,191,64,0.10)" };
    if (val.includes("만료") || val.includes("초과")) return { color: "#B00C0C", bg: "rgba(255,66,66,0.10)" };
    return { color: "#9C5800", bg: "rgba(255,146,0,0.10)" };
  };

  const approvalSteps = ["시스템 초안 생성", "담당자 검토", "사장님 승인", "행정사 전달 준비"];

  return (
    <div className={styles.split}>

      {/* 왼쪽 — 검토 패키지 문서 */}
      <div className={styles.stack}>
        <div style={{
          borderRadius: 12, border: "1px solid rgba(255,146,0,0.30)",
          background: "#fff", borderLeft: "3px solid #FF9200", overflow: "hidden",
        }}>
          {/* 문서 헤더 */}
          <div style={{ padding: "20px 22px 16px 20px" }}>
            <div className={styles.pageHead} style={{ marginBottom: 10 }}>
              <div style={{ flex: 1 }}>
                <div className={styles.subtle} style={{ fontSize: 11.5, marginBottom: 4 }}>행정사 검토용 자료 · 초안</div>
                <h1 className={styles.headline} style={{ fontSize: 18, margin: "0 0 4px" }}>{dynamicPackage.title}</h1>
                <p className={styles.subtle} style={{ fontSize: 12 }}>
                  생성 {dynamicPackage.createdAt} · 수신자 {dynamicPackage.receiver}
                </p>
              </div>
              <span style={{
                display: "inline-flex", padding: "4px 12px", borderRadius: 99, flexShrink: 0,
                fontSize: 12, fontWeight: 700,
                background: "rgba(255,146,0,0.10)", border: "1px solid rgba(255,146,0,0.30)", color: "#9C5800",
              }}>
                {dynamicPackage.status}
              </span>
            </div>

            {/* 개인정보 마스킹 안내 */}
            <div style={{
              padding: "8px 12px", borderRadius: 8, marginBottom: 2,
              background: "rgba(255,146,0,0.07)", border: "1px solid rgba(255,146,0,0.22)",
              fontSize: 12, color: "#9C5800", display: "flex", alignItems: "center", gap: 6,
            }}>
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                <path d="M8 2s5 2 5 6v4l-5 2-5-2V8c0-4 5-6 5-6z" stroke="#FF9200" strokeWidth="1.4" strokeLinejoin="round"/>
              </svg>
              개인정보는 마스킹 처리되어 포함됩니다. 승인 후에도 정부 포털 자동 제출은 수행하지 않습니다.
            </div>
          </div>

          <div style={{ borderTop: "1px solid rgba(112,115,124,0.10)", padding: "0 22px 20px 20px" }}>
            {/* 근로자 기본 정보 */}
            <div style={{ padding: "16px 0 12px" }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#70737C", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 10 }}>
                근로자 기본 정보
              </div>
              {dynamicPackage.profile.map(([key, val]) => (
                <div key={key} style={{ display: "flex", padding: "7px 0", borderBottom: "1px solid rgba(112,115,124,0.07)" }}>
                  <span className={styles.subtle} style={{ width: 140, flexShrink: 0, fontSize: 12.5 }}>{key}</span>
                  <strong style={{ fontSize: 13, color: "#171719" }}>{val}</strong>
                </div>
              ))}
            </div>

            {/* 체류 / 계약 상태 */}
            <div style={{ padding: "12px 0" }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#70737C", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 10 }}>
                체류 / 계약 상태
              </div>
              {dynamicPackage.stay.map(([key, val]) => {
                const ds = docStatusStyle(val);
                return (
                  <div key={key} style={{ display: "flex", alignItems: "center", padding: "7px 0", borderBottom: "1px solid rgba(112,115,124,0.07)" }}>
                    <span className={styles.subtle} style={{ width: 140, flexShrink: 0, fontSize: 12.5 }}>{key}</span>
                    <span style={{ fontSize: 12.5, fontWeight: 600, color: ds.color, background: ds.bg, padding: "2px 8px", borderRadius: 6 }}>{val}</span>
                  </div>
                );
              })}
            </div>

            {/* 제출 서류 */}
            <div style={{ paddingTop: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#70737C", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 10 }}>
                제출 서류
              </div>
              {dynamicPackage.docs.map(([key, val]) => {
                const ds = docStatusStyle(val);
                return (
                  <div key={key} style={{ display: "flex", alignItems: "center", padding: "7px 0", borderBottom: "1px solid rgba(112,115,124,0.07)" }}>
                    <span className={styles.subtle} style={{ width: 140, flexShrink: 0, fontSize: 12.5 }}>{key}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: ds.color, background: ds.bg, padding: "2px 8px", borderRadius: 6 }}>{val}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 오른쪽 사이드바 */}
      <aside className={styles.sideStack}>

        {/* 다음 단계 */}
        <div style={{ padding: "18px", borderRadius: 12, border: "1px solid rgba(112,115,124,0.12)", background: "#fff" }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 14 }}>다음 단계</h2>
          <div className={styles.stack}>
            <button
              type="button"
              style={{
                width: "100%", padding: "11px", borderRadius: 10, border: 0,
                background: "linear-gradient(135deg, #1b3fa0, #00bfa5)",
                color: "#fff", fontSize: 13.5, fontWeight: 700, cursor: "pointer",
                boxShadow: "0 2px 8px rgba(27,63,160,0.25)",
              }}
              onClick={() => onAction?.({ kind: "approval-preview", label: "승인하기" })}
            >
              승인하기
            </button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "revision-request", label: "수정 요청" })}>수정 요청</Button>
            <Button variant="ghost" onClick={() => onAction?.({ kind: "pdf-draft", label: "PDF 내보내기" })}>
              <Download size={15} /> PDF 내보내기
            </Button>
          </div>
        </div>

        {/* 근거 자료 */}
        <div style={{ padding: "18px", borderRadius: 12, border: "1px solid rgba(112,115,124,0.12)", background: "#fff" }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>포함된 근거 (3)</h2>
          <div className={styles.stack}>
            {[
              { grade: "A", source: "국가법령정보센터", text: "출입국관리법 제25조 (체류기간 연장허가)" },
              { grade: "A", source: "출입국관리법",     text: "제94조 벌칙 (체류기간 초과)" },
              { grade: "B", source: "HiKorea",          text: "체류기간 연장허가 신청 안내" },
            ].map((ev) => (
              <div key={ev.text} style={{
                display: "flex", gap: 10, padding: "9px 10px", borderRadius: 8,
                background: "rgba(112,115,124,0.04)", border: "1px solid rgba(112,115,124,0.10)",
              }}>
                <span style={{
                  padding: "1px 7px", borderRadius: 99, fontSize: 11, fontWeight: 700, flexShrink: 0, alignSelf: "flex-start",
                  background: ev.grade === "A" ? "rgba(0,102,255,0.10)" : "rgba(112,115,124,0.10)",
                  border: ev.grade === "A" ? "1px solid rgba(0,102,255,0.25)" : "1px solid rgba(112,115,124,0.20)",
                  color: ev.grade === "A" ? "#003699" : "#70737C",
                }}>{ev.grade}</span>
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: "#171719", marginBottom: 2 }}>{ev.text}</div>
                  <div className={styles.subtle} style={{ fontSize: 11.5 }}>{ev.source}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 승인 흐름 */}
        <div style={{ padding: "18px", borderRadius: 12, border: "1px solid rgba(112,115,124,0.12)", background: "#fff" }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>승인 흐름</h2>
          <div className={styles.stack}>
            {approvalSteps.map((step, i) => {
              const done = i < 2;
              return (
                <div key={step} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{
                    width: 22, height: 22, borderRadius: 99, flexShrink: 0,
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    fontSize: 11, fontWeight: 700,
                    background: done ? "rgba(0,191,64,0.12)" : "rgba(112,115,124,0.10)",
                    color: done ? "#006E25" : "#70737C",
                    border: done ? "1px solid rgba(0,191,64,0.25)" : "1px solid rgba(112,115,124,0.20)",
                  }}>{i + 1}</span>
                  <span style={{ fontSize: 13, fontWeight: done ? 600 : 400, color: done ? "#171719" : "#70737C" }}>{step}</span>
                  {done && (
                    <svg width="12" height="12" viewBox="0 0 14 14" fill="none" style={{ marginLeft: "auto" }}>
                      <path d="M2.5 7l3 3 6-6" stroke="#006E25" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </div>
              );
            })}
          </div>
        </div>
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

function Timeline() {
  const items = ["체류만료일 확인", "누락 서류 감지", "이전 대화 기록 확인", "베트남어 메시지 초안 생성", "대표 승인 요청", "발송 예정 상태로 제한 적용"];
  return <div className={styles.timeline}>{items.map((item, index) => <div className={styles.row} key={item}><span className={cn(styles.dot, styles.toneGreen)} /><div><strong>{item}</strong><div className={styles.subtle}>2026-05-21 10:{10 + index * 3}</div></div></div>)}</div>;
}

