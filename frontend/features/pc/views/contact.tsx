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
import { useSearchParams } from "next/navigation";
import React, { useEffect, useState } from "react";
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

export function ContactView({ onAction }: PcViewProps = {}) {
  const searchParams = useSearchParams();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const requestedWorkerId = searchParams.get("worker_id");
  const requestedWorkerName =
    workers.find((worker) => worker.id === requestedWorkerId)?.name ?? searchParams.get("worker");
  const requestedActionLabel = searchParams.get("label");

  useEffect(() => {
    if (!requestedWorkerName) return;
    const nextIndex = contactItems.findIndex((item) => item.worker === requestedWorkerName);
    if (nextIndex >= 0) setSelectedIndex(nextIndex);
  }, [requestedWorkerName]);

  const statusConfig: Record<string, { bg: string; bd: string; fg: string }> = {
    "초안":    { bg: "rgba(112,115,124,0.08)", bd: "rgba(112,115,124,0.20)", fg: "#70737C" },
    "응답 도착": { bg: "rgba(0,191,64,0.10)",   bd: "rgba(0,191,64,0.25)",   fg: "#006E25" },
    "승인 대기": { bg: "rgba(255,146,0,0.10)",  bd: "rgba(255,146,0,0.30)",  fg: "#9C5800" },
  };
  const selectedContact = contactItems[selectedIndex] ?? contactItems[0];

  return (
    <div className={styles.stack}>

      {/* 헤더 */}
      <div className={styles.pageHead}>
        <div>
          <div className={styles.subtle}>컨택 관리</div>
          <h1 className={styles.headline}>메시지 관리</h1>
          <p className={styles.subtle}>근로자별 다국어 컨택 초안을 확인하고 승인합니다.</p>
        </div>
      </div>

      <div className={styles.contactLayout}>

        {/* 왼쪽 컨택 목록 */}
        <aside className={styles.contactList}>
          <div style={{ padding: "12px 16px", fontSize: 12, fontWeight: 600, color: "#70737C", borderBottom: "1px solid rgba(112,115,124,0.12)" }}>
            컨택 목록 · {contactItems.length}건
          </div>
          {contactItems.map((item, index) => {
            const sc = statusConfig[item.status] ?? statusConfig["초안"];
            const isSelected = selectedIndex === index;
            return (
              <div
                key={item.worker}
                className={styles.contactItem}
                style={{
                  background: isSelected ? "rgba(0,102,255,0.04)" : "transparent",
                  borderLeft: isSelected ? "3px solid #0066FF" : "3px solid transparent",
                  cursor: "pointer",
                }}
                onClick={() => setSelectedIndex(index)}
              >
                <span className={styles.workerAvatar} style={{ flexShrink: 0 }}>{item.initials}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className={styles.badgeLine} style={{ marginBottom: 4 }}>
                    <strong style={{ fontSize: 13.5 }}>{item.worker}</strong>
                    <span style={{
                      fontSize: 10.5, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
                      background: "rgba(124,58,237,0.08)", color: "#7C3AED",
                    }}>{item.country}</span>
                    <span style={{
                      fontSize: 10.5, fontWeight: 700, padding: "1px 6px", borderRadius: 4,
                      background: "rgba(0,102,255,0.10)", color: "#003699",
                    }}>{item.badge}</span>
                  </div>
                  <div className={styles.subtle} style={{ fontSize: 12, marginBottom: 6, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.desc}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{
                      display: "inline-flex", padding: "2px 8px", borderRadius: 99,
                      fontSize: 11, fontWeight: 700,
                      background: sc.bg, border: `1px solid ${sc.bd}`, color: sc.fg,
                    }}>{item.status}</span>
                    <span className={styles.subtle} style={{ fontSize: 11 }}>{item.date}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </aside>

        {/* 오른쪽 메시지 상세 */}
        <section style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {requestedWorkerName ? (
            <div style={{ padding: "10px 14px", borderRadius: 10, background: "#EFF6FF", border: "1px solid #BFDBFE", color: "#1E3A8A", fontSize: 12.5, fontWeight: 700, marginBottom: 10 }}>
              오늘 할 일에서 이동: {requestedWorkerName} · {requestedActionLabel ?? "컨택 확인"}
            </div>
          ) : null}

          {/* 문서 헤더 */}
          <div className={styles.document}>
            <div className={styles.pageHead}>
              <div>
                <div className={styles.titleLine} style={{ marginBottom: 4 }}>
                  <span style={{
                    fontSize: 11, fontWeight: 700, padding: "2px 6px", borderRadius: 4,
                    background: "rgba(124,58,237,0.08)", color: "#7C3AED",
                  }}>VN</span>
                  <h2 style={{ fontSize: 17, fontWeight: 700, margin: 0 }}>{selectedContact.worker}</h2>
                </div>
                <p className={styles.subtle} style={{ fontSize: 12.5 }}>{selectedContact.country} · Zalo · {selectedContact.worker}</p>
              </div>
              <span style={{
                display: "inline-flex", padding: "3px 10px", borderRadius: 99,
                fontSize: 11.5, fontWeight: 700,
                background: "rgba(112,115,124,0.08)", border: "1px solid rgba(112,115,124,0.20)", color: "#70737C",
              }}>{selectedContact.status}</span>
            </div>

            {/* 발송 전 안내 */}
            <div style={{
              padding: "10px 14px", borderRadius: 9,
              background: "rgba(0,102,255,0.05)",
              border: "1px solid rgba(0,102,255,0.15)",
              fontSize: 12.5, color: "#003699", fontWeight: 500,
            }}>
              승인 전에는 외부로 발송되지 않습니다. 담당자 검토용 초안입니다.
            </div>
          </div>

          {/* 메시지 본문 */}
          <div className={styles.document}>
            <div className={styles.buttonRow} style={{ marginBottom: 12 }}>
              <button type="button" style={{
                padding: "5px 14px", borderRadius: 7, border: "1px solid #0066FF",
                background: "#0066FF", color: "#fff", fontSize: 12.5, fontWeight: 600, cursor: "pointer",
              }}>Tiếng Việt</button>
              <button type="button" style={{
                padding: "5px 14px", borderRadius: 7, border: "1px solid rgba(112,115,124,0.20)",
                background: "#fff", color: "#374151", fontSize: 12.5, fontWeight: 500, cursor: "pointer",
              }}>한국어</button>
            </div>
            <div className={styles.messageBox}>
              Xin chào anh Nguyen V.,<br /><br />
              Đây là Oegobanjang.<br />
              Chúng tôi đang chuẩn bị gia hạn thời gian cư trú.<br />
              Vui lòng gửi các giấy tờ sau trước ngày 20 tháng 5.<br /><br />
              1. Bản sao hộ chiếu (trang ảnh)<br />
              2. Bản sao thẻ đăng ký người nước ngoài (mặt trước &amp; mặt sau)<br /><br />
              Mục đích thu thập: Chuẩn bị hồ sơ gia hạn cư trú.<br />
              Thời gian lưu giữ: 30 ngày sau khi nộp hồ sơ.
            </div>

            {/* 예상 응답 시나리오 */}
            <h3 style={{ fontSize: 13, fontWeight: 700, margin: "16px 0 10px", color: "#374151" }}>예상 응답 시나리오</h3>
            <div className={styles.scenarioGrid}>
              <Scenario title="긍정 응답" desc="서류 수신 후 반영 후보 생성 / 담당자 확인 후 반영" tone="green" />
              <Scenario title="추가 정보 요청" desc="필요 서류와 형식 기준을 다시 안내" tone="blue" />
              <Scenario title="응답 지연" desc="2일 뒤 리마인드 메시지 제안" tone="orange" />
            </div>
          </div>

          {/* 하단 CTA */}
          <div style={{ padding: "14px 20px", borderTop: "1px solid rgba(112,115,124,0.10)", display: "flex", gap: 10, alignItems: "center" }}>
            <Button variant="ghost" onClick={() => onAction?.({ kind: "response-summary", label: "나중에 보기" })}>나중에 보기</Button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "revision-request", label: "수정 요청" })}>수정 요청</Button>
            <button
              type="button"
              style={{
                padding: "8px 20px", borderRadius: 9, border: 0,
                background: "linear-gradient(135deg, #1b3fa0, #00bfa5)",
                color: "#fff", fontSize: 13.5, fontWeight: 700, cursor: "pointer",
              }}
              onClick={() => onAction?.({ kind: "approval-preview", label: "승인" })}
            >
              승인
            </button>
          </div>
        </section>
      </div>
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

