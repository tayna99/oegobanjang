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

export function TodayTasksView({ onAction }: PcViewProps = {}) {
  const [selectedWorkerId, setSelectedWorkerId] = useState("w_nguyen");
  const [selectedSummaryId, setSelectedSummaryId] = useState("visa");
  const [detailOpen, setDetailOpen] = useState(true);
  const selectedWorker = workers.find((worker) => worker.id === selectedWorkerId) ?? workers[0];

  function selectSummary(item: (typeof summary)[number]) {
    setSelectedSummaryId(item.id);
    setSelectedWorkerId(item.workerId);
    setDetailOpen(true);
  }

  function selectWorker(workerId: string) {
    setSelectedSummaryId("");
    setSelectedWorkerId(workerId);
    setDetailOpen(true);
  }

  return (
    <div className={cn(styles.todayDashboard, !detailOpen && styles.todayDashboardCollapsed)}>
      <section className={styles.stack}>

        {/* 브리핑 배너 */}
        <div style={{
          display: "flex", alignItems: "center", gap: 14,
          padding: "14px 18px", borderRadius: 12,
          background: "linear-gradient(90deg, rgba(27,63,160,0.07), rgba(0,191,165,0.04))",
          border: "1px solid rgba(27,63,160,0.15)",
        }}>
          <span className={styles.gradientMark} style={{ width: 36, height: 36, borderRadius: 10, fontSize: 14 }}>반</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 2 }}>오늘 브리핑이 준비되었습니다</div>
            <div className={styles.subtle} style={{ fontSize: 12.5, lineHeight: 1.5 }}>
              외고반장이 {totalRiskCaseCount}개 케이스를 정리했습니다. 즉시 확인 1건, 우선 확인 3건, 승인 대기 5건.
            </div>
          </div>
          <span className={styles.subtle} style={{ fontSize: 12, flexShrink: 0 }}>오전 08:31</span>
          <Button variant="secondary" onClick={() => onAction?.({ kind: "refresh", label: "다시 생성" })}>
            <RefreshCcw size={14} /> 다시 생성
          </Button>
        </div>

        {/* 요약 카드 7칸 */}
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

        {/* 필터 Chip 바 */}
        <div className={styles.sectionTitle}>
          <div className={styles.buttonRow}>
            <button className={cn(styles.chip, styles.chipActive)} type="button">전체</button>
            <button className={styles.chip} type="button">즉시 확인 <span className={styles.chipCount}>1</span></button>
            <button className={styles.chip} type="button">우선 확인 <span className={styles.chipCount}>3</span></button>
            <button className={styles.chip} type="button">확인 필요 <span className={styles.chipCount}>2</span></button>
            <button className={styles.chip} type="button">참고 <span className={styles.chipCount}>1</span></button>
          </div>
          <div className={styles.buttonRow}>
            <button className={styles.chip} type="button">전체 라인</button>
            <button className={styles.chip} type="button">승인 대기만</button>
            <button className={styles.chip} type="button">서류 보완 필요</button>
          </div>
        </div>

        {/* 업무 큐 */}
        <div className={styles.taskQueueWrap}>
          <div className={styles.taskQueueHead}>
            오늘의 업무 큐
            <span className={styles.taskQueueHeadCount}>{todaysTasks.length}건</span>
          </div>
          <div className={styles.taskQueue}>
            <div className={styles.taskQueueHeader}>
              <div /><div>업무</div><div>대상</div><div>상태</div><div>기한</div><div>다음 처리</div><div />
            </div>
            {todaysTasks.map((task, i) => {
              const st = TASK_STATUS_MAP[task.status] ?? { label: task.status, bg: "#F8FAFC", fg: "#64748B" };
              const isUrgent = task.deadline.startsWith("D-") && parseInt(task.deadline.slice(2)) <= 30;
              const matchedWorker = workers.find((w) => w.name.startsWith(task.target.split(" ")[0]));
              const isSelected = matchedWorker && selectedWorkerId === matchedWorker.id;
              return (
                <div
                  key={task.kind + String(i)}
                  className={cn(styles.taskQueueRow, isSelected && styles.taskQueueRowSelected)}
                  onClick={() => { if (matchedWorker) selectWorker(matchedWorker.id); }}
                >
                  <div className={styles.taskCheckbox} />
                  <div className={styles.taskTitleCell}>
                    <div className={styles.taskTypeIcon}>{TASK_TYPE_ICON[task.kind] ?? null}</div>
                    <span className={styles.taskTitle}>{task.title}</span>
                  </div>
                  <div className={styles.taskTarget}>{task.target}</div>
                  <span className={styles.taskStatusPill} style={{ background: st.bg, color: st.fg }}>{st.label}</span>
                  <div className={isUrgent ? styles.taskDeadlineUrgent : styles.taskDeadlineNormal}>{task.deadline}</div>
                  <button
                    className={styles.taskNextBtn}
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onAction?.({ kind: actionForNext(task.next), label: task.next }); }}
                  >
                    {task.next}
                  </button>
                  <button className={styles.taskMoreBtn} type="button"><MoreHorizontal size={14} /></button>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {detailOpen ? (
        <TodayWorkerDetail onAction={onAction} onClose={() => setDetailOpen(false)} worker={selectedWorker} />
      ) : null}
    </div>
  );
}

function TodayWorkerDetail({
  onAction,
  onClose,
  worker,
}: {
  onAction?: (action: PcViewAction) => void;
  onClose: () => void;
  worker: (typeof workers)[number];
}) {
  const isNguyen = worker.id === "w_nguyen";
  const isBayar = worker.id === "w_bayar";
  const risks = isNguyen
    ? [
        {
          title: "체류만료 임박",
          desc: "체류만료까지 30일 남았습니다. 연장 신청 또는 자진 출국 검토가 필요합니다.",
          basis: ["출입국관리법 제25조", "체류기간 연장허가 신청 안내"],
        },
        {
          title: "필수서류 누락",
          desc: "여권 사본, 외국인등록증 사본 보완이 필요합니다.",
          basis: ["외국인근로자 고용 시 보유 서류"],
        },
      ]
    : [
        {
          title: isBayar ? "체류만료 초과" : "확인 필요",
          desc: isBayar ? "체류만료일이 지났습니다. 담당자 확인과 검토 자료 정리가 필요합니다." : "계약·체류·서류 상태를 담당자가 확인해야 합니다.",
          basis: isBayar ? ["출입국관리법 제25조", "제94조 벌칙"] : ["근로자 프로필", "체류 정보"],
        },
      ];
  const docs: Array<[string, string, Tone]> = isNguyen
    ? [
        ["여권사본", "보완 필요", "orange" as Tone],
        ["외국인등록증", "보완 필요", "orange" as Tone],
        ["근로계약서", "확보됨", "green" as Tone],
        ["건강진단서", "확보됨", "green" as Tone],
      ]
    : [
        ["여권사본", "확보됨", "green" as Tone],
        ["외국인등록증", "확보됨", "green" as Tone],
        ["근로계약서", "확보됨", "green" as Tone],
        ["건강진단서", isBayar ? "만료" : "확보됨", isBayar ? "orange" as Tone : "green" as Tone],
      ];

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
        {risks.slice(0, 2).map((r) => (
          <div className={styles.reasonItem} key={r.title}>
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
        {["필수 서류 체크리스트 검토 완료", "유사 케이스 기반 보완 포인트 도출 완료"].map((item) => (
          <div className={styles.aiPrepItem} key={item}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M3 8l3.5 3.5 6.5-7" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {item}
          </div>
        ))}
      </section>

      <section className={styles.detailSection}>
        <h3>현재 리스크 <Badge tone="gray">{risks.length}</Badge></h3>
        <div className={styles.stack}>
          {risks.map((risk) => (
            <Card className={styles.riskCard} key={risk.title}>
              <div className={styles.sectionTitle}>
                <strong>{risk.title}</strong>
                <Badge tone={worker.statusTone}>{worker.status}</Badge>
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
          <Card className={styles.panel}><div className={styles.subtle}>체류만료일</div><strong>{worker.visaExpiry}</strong><div className={styles.textOrange}>{worker.dday}</div></Card>
          <Card className={styles.panel}><div className={styles.subtle}>계약종료일</div><strong>{worker.contractEnd}</strong><div className={styles.subtle}>{isNguyen ? "D-145" : worker.dday}</div></Card>
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>제출 서류 <Badge tone="gray">{docs.length}</Badge></h3>
        <div className={styles.stack}>
          {docs.map(([name, status, tone]) => (
            <div className={cn(styles.docRow, styles.panel)} key={name}>
              <span><FileText size={16} /> {name}</span>
              <Badge tone={tone}>{status}</Badge>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>추천 액션 <Badge tone="gray">3</Badge></h3>
        <div className={styles.stack}>
          <Card className={styles.actionCard}>
            <div>
              <strong>서류 요청 초안 보기 (베트남어 포함)</strong>
              <p className={styles.subtle}>대상: {worker.name}</p>
            </div>
            <div className={styles.buttonRow}>
              <Button data-testid="action-draft" variant="secondary" onClick={() => onAction?.({ kind: "document-draft", label: "초안 보기" })}>초안 보기</Button>
              <Button data-testid="action-approval" onClick={() => onAction?.({ kind: "approval-preview", label: "승인" })}>승인</Button>
            </div>
          </Card>
          <Card className={styles.actionCard}>
            <div>
              <strong>체류기간 연장 검토 자료 만들기</strong>
              <p className={styles.subtle}>대상: {worker.name}</p>
            </div>
            <Button data-testid="action-handoff" variant="secondary" onClick={() => onAction?.({ kind: "handoff-preview", label: "검토 자료 보기" })}>검토 자료 보기</Button>
          </Card>
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>근거 자료 <Badge tone="gray">3</Badge></h3>
        <div className={styles.stack}>
          <Evidence source="국가법령정보센터" text="출입국관리법 제25조 (체류기간 연장허가)" grade="A" />
          <Evidence source="HiKorea" text="체류기간 연장허가 신청 안내" grade="B" />
          <Evidence source="EPS 고용허가제" text="외국인근로자 고용 시 보유 서류" grade="B" />
        </div>
      </section>

      <section className={styles.detailSection}>
        <h3>업무 기록</h3>
        <div className={styles.timeline}>
          {["Bayar M. 케이스 승인 요청", "오늘 브리핑 7건 생성", `${worker.name} 리스크 플래그`, "CSV 업로드 — 24명 동기화"].map((item, index) => (
            <div className={styles.row} key={item}><span className={cn(styles.dot, index === 0 ? styles.toneBlue : styles.toneGray)} /><div><strong>{item}</strong><div className={styles.subtle}>{index === 0 ? "08:14 · 김민수 차장" : index === 1 ? "08:01 · 시스템" : "08:00 · 시스템"}</div></div></div>
          ))}
        </div>
      </section>

      {/* 하단 CTA */}
      <div className={styles.detailPanelCta}>
        <button
          className={styles.taskCtaBtn}
          type="button"
          onClick={() => onAction?.({ kind: "approval-preview", label: "대표 승인 요청" })}
        >
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
            <path d="M17 11v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h6M13 3h5v5M8 12l9-9" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          대표 승인 요청
        </button>
        <Button variant="secondary" onClick={() => onAction?.({ kind: "revision-request", label: "수정 요청" })}>수정 요청</Button>
      </div>
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

