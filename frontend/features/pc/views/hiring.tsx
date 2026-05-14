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
import React, { useState } from "react";
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

function actionForNext(next: string): PcActionKind {
  if (next.includes("초안")) return "document-draft";
  if (next.includes("요청서")) return "handoff-preview";
  if (next.includes("승인")) return "approval-preview";
  if (next.includes("응답")) return "response-summary";
  return "handoff-preview";
}

function workerTestId(workerId: string) {
  return `worker-row-${workerId.replace("w_", "")}`;
}

export function HiringPreparationView({ onAction }: PcViewProps = {}) {
  const hiringCards = [
    {
      title: "신규 E-9 3명 채용 준비",
      meta: "화성 1공장 · 조립라인 · 행정사 검토 전 확인 필요",
      deadline: "2026.05.20", percent: 72, done: "5/8 완료",
      status: "준비 중", tone: "blue",
      dot: "#0066FF", fg: "#003699", bg: "rgba(0,102,255,0.07)", bd: "rgba(0,102,255,0.20)",
      tasks: ["구인노력 기간 확인", "고용허가 신청서 준비", "채용 요청서 확인"],
    },
    {
      title: "Candidate A 입국 전 서류 패키지",
      meta: "화성 1공장 · 도장라인 · 행정사 검토 전 확인 필요",
      deadline: "2026.05.20", percent: 45, done: "2/5 완료",
      status: "검토 필요", tone: "orange",
      dot: "#FF9200", fg: "#9C5800", bg: "rgba(255,146,0,0.10)", bd: "rgba(255,146,0,0.30)",
      tasks: ["건강진단서 원본 확인", "입국 전 교육 수료증 확인", "근로계약서 사본 확인"],
    },
  ];

  return (
    <div className={styles.stack}>

      {/* 헤더 */}
      <div>
        <div className={styles.subtle}>채용 준비</div>
        <h1 className={styles.headline}>신규 고용 준비</h1>
        <p className={styles.subtle}>신규 고용 준비 상태를 점검합니다. 후보자 점수화나 추천은 하지 않습니다.</p>
      </div>

      {/* 브리핑 배너 */}
      <div style={{
        display: "flex", alignItems: "center", gap: 14,
        padding: "14px 18px", borderRadius: 12,
        background: "linear-gradient(90deg, rgba(27,63,160,0.07), rgba(0,191,165,0.04))",
        border: "1px solid rgba(27,63,160,0.15)",
      }}>
        <span className={styles.gradientMark} style={{ width: 36, height: 36, borderRadius: 10, fontSize: 14 }}>반</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 2 }}>신규 채용 준비 2건 진행 중</div>
          <div className={styles.subtle} style={{ fontSize: 12.5 }}>검토 필요 1건 · 준비 중 1건</div>
        </div>
      </div>

      {/* 채용 카드 */}
      {hiringCards.map((card) => (
        <div
          key={card.title}
          style={{
            borderRadius: 12,
            border: `1px solid ${card.bd}`,
            background: "#fff",
            borderLeft: `3px solid ${card.dot}`,
            padding: "20px 22px 20px 20px",
          }}
        >
          {/* 카드 헤더 */}
          <div className={styles.pageHead} style={{ marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <div className={styles.badgeLine} style={{ marginBottom: 6 }}>
                <span style={{
                  display: "inline-flex", padding: "2px 8px", borderRadius: 6,
                  fontSize: 11, fontWeight: 600, background: "rgba(112,115,124,0.08)", color: "#374151",
                }}>E-9 · 3명</span>
                <span style={{
                  display: "inline-flex", padding: "2px 8px", borderRadius: 6,
                  fontSize: 11, fontWeight: 700,
                  background: card.bg, border: `1px solid ${card.bd}`, color: card.fg,
                }}>{card.status}</span>
              </div>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>{card.title}</h2>
              <p className={styles.subtle} style={{ fontSize: 12.5 }}>{card.meta}</p>
            </div>
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <div className={styles.subtle} style={{ fontSize: 11 }}>마감</div>
              <strong style={{ fontSize: 14 }}>{card.deadline}</strong>
            </div>
          </div>

          {/* 진행률 바 */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12.5, color: "#374151" }}>준비 완료도</span>
              <strong style={{ fontSize: 14, fontWeight: 800, color: card.dot }}>{card.percent}%</strong>
            </div>
            <div className={styles.progressTrack}>
              <div className={styles.progressBar} style={{ width: `${card.percent}%`, background: card.dot }} />
            </div>
            <p className={styles.subtle} style={{ fontSize: 12, marginTop: 4 }}>{card.done}</p>
          </div>

          {/* 남은 체크리스트 */}
          <div className={styles.stack} style={{ marginBottom: 16 }}>
            {card.tasks.map((task) => (
              <div key={task} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "10px 14px", borderRadius: 8,
                background: "rgba(112,115,124,0.05)", border: "1px solid rgba(112,115,124,0.10)",
              }}>
                <span style={{
                  width: 18, height: 18, borderRadius: 5, flexShrink: 0,
                  border: `1.5px solid ${card.bd}`, background: card.bg,
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                }}>
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2.5 2.5L8 3" stroke={card.dot} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                <span style={{ fontSize: 13, color: "#374151" }}>{task}</span>
              </div>
            ))}
          </div>

          {/* 액션 버튼 */}
          <div className={styles.buttonRow}>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "handoff-preview", label: "요청서 보기" })}>
              <FileText size={15} /> 요청서 보기
            </Button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "approval-preview", label: "행정사 검토 요청" })}>
              <Check size={15} /> 행정사 검토 요청
            </Button>
            <span className={styles.subtle} style={{ fontSize: 12, marginLeft: "auto" }}>남은 작업 {card.tasks.length}개</span>
          </div>
        </div>
      ))}
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

