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
import { adminPackage, contactItems, judgmentRows, riskCases, todaysTasks, workers as seedWorkers, type Tone } from "../data";
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

export function WorkersView({ onAction }: PcViewProps = {}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dbWorkers, setDbWorkers] = useState<Array<{ id: string; name: string; nationality?: string; language_code?: string; visa_type?: string }>>([]);
  const [documentRequests, setDocumentRequests] = useState<Array<{ worker_id: string; doc_type: string; status: string }>>([]);
  useEffect(() => {
    void Promise.all([
      fetch("/api/v1/contact/workers?company_id=550e8400-e29b-41d4-a716-446655440001", { cache: "no-store" })
        .then((response) => response.ok ? response.json() : { workers: [] }),
      fetch("/api/v1/documents/worker-requests/all?company_id=550e8400-e29b-41d4-a716-446655440001", { cache: "no-store" })
        .then((response) => response.ok ? response.json() : { requests: [] }),
    ])
      .then(([workerData, documentData]) => {
        setDbWorkers(workerData.workers ?? []);
        setDocumentRequests(documentData.requests ?? []);
      })
      .catch(() => {
        setDbWorkers([]);
        setDocumentRequests([]);
      });
  }, []);
  const workerRows = useMemo(() => {
    const seen = new Set(seedWorkers.map((worker) => worker.id));
    const documentsByWorker = new Map<string, Array<{ doc_type: string; status: string }>>();
    for (const request of documentRequests) {
      const rows = documentsByWorker.get(request.worker_id) ?? [];
      rows.push(request);
      documentsByWorker.set(request.worker_id, rows);
    }
    const mergeDocumentStatus = (worker: (typeof seedWorkers)[number]) => {
      const requests = documentsByWorker.get(worker.id) ?? [];
      if (requests.length === 0) return worker;
      const requestedCount = requests.filter((request) => request.status === "REQUESTED" || request.status === "MISSING" || request.status === "REJECTED").length;
      const submittedCount = requests.filter((request) => request.status === "SUBMITTED").length;
      const hasOpenRequest = requestedCount > 0;
      const hasSubmitted = submittedCount > 0;
      return {
        ...worker,
        docExtra: hasOpenRequest ? `+${requestedCount}` : "",
        status: hasOpenRequest ? worker.status : hasSubmitted ? "서류 제출됨" : worker.status,
        statusTone: hasOpenRequest ? worker.statusTone : hasSubmitted ? ("green" as Tone) : worker.statusTone,
      };
    };
    const added = dbWorkers
      .filter((worker) => !seen.has(worker.id))
      .map((worker) => ({
        id: worker.id,
        initials: (worker.name || "근").slice(0, 1).toUpperCase(),
        name: worker.name || "근로자",
        localName: "신규 등록",
        nationalityCode: (worker.language_code || "VI").toUpperCase(),
        nationality: worker.nationality || "-",
        visaType: worker.visa_type || "E-9",
        line: "등록 정보 확인 필요",
        visaExpiry: "-",
        contractEnd: "-",
        dday: "-",
        status: "정상",
        statusTone: "green" as Tone,
        tenure: "-",
        docs: [],
        docExtra: "",
      }));
    return [...seedWorkers.map(mergeDocumentStatus), ...added];
  }, [dbWorkers, documentRequests]);
  const missingDocumentCount = workerRows.reduce((total, worker) => {
    const rawCount = worker.docExtra?.replace("+", "") ?? "0";
    const count = Number.parseInt(rawCount, 10);
    return total + (Number.isFinite(count) ? count : 0);
  }, 0);
  const needsAttentionCount = workerRows.filter((worker) => worker.statusTone === "red" || worker.statusTone === "orange").length;
  const normalCount = workerRows.filter((worker) => worker.statusTone === "green").length;

  const statCards: Array<[string, string, string, string]> = [
    ["전체 등록", `${workerRows.length}명`, "#1D4ED8", "#EFF6FF"],
    ["즉시·우선 확인", `${needsAttentionCount}명`, "#C2410C", "#FFF7ED"],
    ["서류 보완 필요", `${missingDocumentCount}건`, "#B00C0C", "#FEF2F2"],
    ["정상", `${normalCount}명`, "#065F46", "#ECFDF5"],
  ];

  // doc tile 색상: 근로자 위험도 기준 간이 매핑
  function docTileStyle(workerTone: string, hasExtra: boolean): { bg: string; color: string } {
    if (workerTone === "red" || workerTone === "orange") {
      return hasExtra
        ? { bg: "rgba(255,146,0,0.14)", color: "#9C5800" }
        : { bg: "rgba(0,191,64,0.12)", color: "#006E25" };
    }
    return { bg: "rgba(0,191,64,0.12)", color: "#006E25" };
  }

  return (
    <div className={styles.stack}>

      {/* 헤더 */}
      <div className={styles.pageHead}>
        <div>
          <div className={styles.subtle}>근로자 목록</div>
          <h1 className={styles.headline}>전체 근로자 · {workerRows.length}명</h1>
        </div>
        <Button variant="secondary" onClick={() => onAction?.({ kind: "worker-register", label: "근로자 등록" })}>
          <UserRoundPlus size={15} /> 근로자 등록
        </Button>
      </div>

      {/* 요약 지표 카드 */}
      <div className={styles.metricGrid}>
        {statCards.map(([title, value, fg, bg]) => (
          <div key={title} style={{ padding: "14px 16px", borderRadius: 12, border: "1px solid rgba(112,115,124,0.12)", background: "#fff" }}>
            <div className={styles.subtle} style={{ fontSize: 12, marginBottom: 6 }}>{title}</div>
            <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.03em", color: fg, background: bg, borderRadius: 8, padding: "2px 10px", display: "inline-block" }}>{value}</div>
          </div>
        ))}
      </div>

      {/* 근로자 그리드 테이블 */}
      <div className={styles.workerGrid}>
        {/* 헤더 행 */}
        <div className={styles.workerGridHeader}>
          <div>근로자</div>
          <div>국적·체류</div>
          <div>체류만료 / D-day</div>
          <div>계약 종료</div>
          <div>서류</div>
          <div>위험도</div>
          <div style={{ textAlign: "right" }}>다음 처리</div>
        </div>

        {/* 데이터 행 */}
        {workerRows.map((worker) => {
          const isCritical = worker.statusTone === "red";
          const isSelected = selectedId === worker.id;
          const sev = CASE_SEV[worker.statusTone] ?? CASE_SEV.gray;
          const hasExtra = !!worker.docExtra;
          const docStyle = docTileStyle(worker.statusTone, hasExtra);
          const dDayIsOver = worker.dday.includes("+");

          return (
            <div
              key={worker.id}
              className={cn(
                styles.workerGridRow,
                isCritical && styles.workerGridRowCritical,
                isSelected && styles.workerGridRowSelected,
              )}
              onClick={() => setSelectedId(isSelected ? null : worker.id)}
            >
              {/* 근로자 */}
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span className={styles.workerAvatar} style={{ flexShrink: 0 }}>{worker.initials}</span>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, display: "flex", alignItems: "center", gap: 5 }}>
                    {worker.name}
                    <span className={styles.muted} style={{ fontWeight: 400, fontSize: 12 }}>· {worker.localName}</span>
                  </div>
                  <div className={styles.subtle} style={{ fontSize: 12, marginTop: 1 }}>{worker.line}</div>
                </div>
              </div>

              {/* 국적·체류 */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{worker.nationalityCode} {worker.nationality}</div>
                <div className={styles.subtle} style={{ fontSize: 11.5, marginTop: 2 }}>{worker.visaType}</div>
              </div>

              {/* 체류만료 / D-day */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{worker.visaExpiry}</div>
                <div style={{ fontSize: 12, fontWeight: 700, marginTop: 3, color: dDayIsOver ? "#B00C0C" : sev.fg }}>
                  {worker.dday}
                </div>
              </div>

              {/* 계약 종료 */}
              <div>
                <div style={{ fontSize: 13 }}>{worker.contractEnd}</div>
                <div className={styles.subtle} style={{ fontSize: 11, marginTop: 2 }}>{worker.dday}</div>
              </div>

              {/* 서류 타일 */}
              <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
                {worker.docs.map((doc, di) => {
                  const tileStyle = hasExtra && di >= worker.docs.length - parseInt(worker.docExtra?.replace("+","") ?? "0")
                    ? { bg: "rgba(255,66,66,0.12)", color: "#B00C0C" }
                    : docStyle;
                  return (
                    <span key={doc} className={styles.workerDocTile} style={{ background: tileStyle.bg, color: tileStyle.color }}>
                      {doc}
                    </span>
                  );
                })}
                {worker.docExtra && (
                  <span style={{ fontSize: 11, fontWeight: 600, color: "#C2410C", marginLeft: 2 }}>{worker.docExtra} 보완</span>
                )}
              </div>

              {/* 위험도 pill */}
              <div>
                <span style={{
                  display: "inline-flex", alignItems: "center", padding: "3px 9px",
                  borderRadius: 99, fontSize: 11.5, fontWeight: 700,
                  background: sev.bg, border: `1px solid ${sev.bd}`, color: sev.fg,
                }}>
                  {worker.status}
                </span>
                <div className={styles.subtle} style={{ fontSize: 11, marginTop: 3 }}>근속 {worker.tenure}</div>
              </div>

              {/* 처리 버튼 */}
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  className={styles.workerProcessBtn}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onAction?.({ kind: "handoff-preview", label: `${worker.name} 처리` });
                  }}
                >
                  처리
                </button>
              </div>
            </div>
          );
        })}
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

