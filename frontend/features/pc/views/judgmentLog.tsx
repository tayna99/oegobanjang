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

export function JudgmentLogView({ onAction }: PcViewProps = {}) {
  const [selectedId, setSelectedId] = useState("#4789");

  const statusStyle: Record<string, { bg: string; fg: string }> = {
    "승인 완료":    { bg: "rgba(0,191,64,0.10)",  fg: "#006E25" },
    "발송 예정":    { bg: "rgba(0,102,255,0.07)", fg: "#003699" },
    "수정 요청":    { bg: "rgba(255,146,0,0.10)", fg: "#9C5800" },
    "담당자 확인":  { bg: "rgba(0,102,255,0.07)", fg: "#003699" },
    "승인 대기":    { bg: "rgba(255,146,0,0.10)", fg: "#9C5800" },
    "검토 자료 준비": { bg: "rgba(112,115,124,0.08)", fg: "#70737C" },
  };

  const selected = judgmentRows.find((r) => r.id === selectedId) ?? judgmentRows[0];

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
          <button className={styles.chip} type="button">승인 대기 <span className={styles.chipCount}>2</span></button>
          <button className={styles.chip} type="button">발송 예정 <span className={styles.chipCount}>2</span></button>
          <button className={styles.chip} type="button">행정사 검토 <span className={styles.chipCount}>1</span></button>
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
            display: "grid", gridTemplateColumns: "28px 80px 1fr 110px 90px",
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
          {judgmentRows.map((row) => {
            const ss = statusStyle[row.status] ?? { bg: "rgba(112,115,124,0.08)", fg: "#70737C" };
            const isSelected = row.id === selectedId;
            return (
              <div
                key={row.id}
                style={{
                  display: "grid", gridTemplateColumns: "28px 80px 1fr 110px 90px",
                  padding: "11px 14px", gap: 10, alignItems: "center",
                  borderBottom: "1px solid rgba(112,115,124,0.08)",
                  background: isSelected ? "rgba(0,102,255,0.04)" : "transparent",
                  cursor: "pointer", transition: "background 0.15s",
                  borderLeft: isSelected ? "2px solid #0066FF" : "2px solid transparent",
                }}
                onClick={() => setSelectedId(row.id)}
              >
                <div><input type="checkbox" aria-label={`${row.id} 선택`} onClick={(e) => e.stopPropagation()} /></div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#1D4ED8" }}>{row.id}</div>
                <div style={{ fontSize: 13 }}>{row.worker}</div>
                <div>
                  <span style={{
                    display: "inline-flex", padding: "2px 9px", borderRadius: 99,
                    fontSize: 11.5, fontWeight: 700,
                    background: ss.bg, color: ss.fg,
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
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>판단 기록 {selected.id}</h2>
            <span style={{
              display: "inline-flex", padding: "3px 10px", borderRadius: 99,
              fontSize: 11.5, fontWeight: 700,
              background: (statusStyle[selected.status] ?? { bg: "rgba(112,115,124,0.08)" }).bg,
              color: (statusStyle[selected.status] ?? { fg: "#70737C" }).fg,
            }}>{selected.status}</span>
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
          {[["담당자", "김대리 (인사팀)"], ["대상 근로자", "Nguyen V."], ["관련 케이스", "체류기간 연장 서류 요청"]].map(([label, val]) => (
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
          <div style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(0,102,255,0.05)", border: "1px solid rgba(0,102,255,0.15)", fontSize: 13.5, lineHeight: 1.65, color: "#374151" }}>
            체류만료일이 45일 이내로 확인되어, 누락된 서류 요청 초안을 만들고 실제 전달 전 대표 승인이 완료됐습니다.
          </div>
        </section>

        {/* 사용한 정보 */}
        <section style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <CheckCircle size={14} color="#0066FF" />
            <strong style={{ fontSize: 13, fontWeight: 700 }}>사용한 정보</strong>
          </div>
          <div className={styles.badgeLine}>
            {["근로자 프로필", "체류 정보", "케이스 정보", "이전 대화 기록", "서류 체크리스트"].map((tag) => (
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
          <div style={{ padding: "12px 14px", borderRadius: 10, background: "#fff", border: "1px solid rgba(112,115,124,0.12)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong style={{ fontSize: 13 }}>대표 (서류 요청 초안)</strong>
                <p className={styles.subtle} style={{ fontSize: 12, margin: "2px 0 0" }}>김대표 · 2026-05-21 10:42</p>
              </div>
              <span style={{ padding: "3px 10px", borderRadius: 99, fontSize: 11.5, fontWeight: 700, background: "rgba(0,191,64,0.10)", color: "#006E25" }}>승인 완료</span>
            </div>
          </div>
        </section>

        {/* 이벤트 타임라인 */}
        <section>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <CheckCircle size={14} color="#0066FF" />
            <strong style={{ fontSize: 13, fontWeight: 700 }}>이벤트 타임라인</strong>
          </div>
          <Timeline />
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

function Timeline() {
  const items = ["체류만료일 확인", "누락 서류 감지", "이전 대화 기록 확인", "베트남어 메시지 초안 생성", "대표 승인 요청", "발송 예정 상태로 제한 적용"];
  return <div className={styles.timeline}>{items.map((item, index) => <div className={styles.row} key={item}><span className={cn(styles.dot, styles.toneGreen)} /><div><strong>{item}</strong><div className={styles.subtle}>2026-05-21 10:{10 + index * 3}</div></div></div>)}</div>;
}

