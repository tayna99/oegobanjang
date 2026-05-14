import {
  Check,
  CheckCircle,
  Clock3,
  Download,
  FileText,
  MessageSquare,
  MoreHorizontal,
  RefreshCcw,
  Search,
  Shield,
  UserRoundPlus,
  X,
} from "lucide-react";
import { useState } from "react";
import { adminPackage, company, contactItems, judgmentRows, riskCases, todaysTasks, workers, type Tone } from "./data";
import { Badge, Button, Card, cn, IconTile, PillButton, textToneClass, toneClass } from "./ui";
import styles from "./PcShell.module.css";

// workers 배열에서 통계 계산
const urgentWorkers = workers.filter((w) => w.statusTone === "red" || w.statusTone === "orange");
const docWorkers = workers.filter((w) => w.docExtra != null);
const normalWorkers = workers.filter((w) => w.statusTone === "green");
const firstUrgentId = urgentWorkers[0]?.id ?? workers[0]?.id ?? "";
const firstDocId = docWorkers[0]?.id ?? workers[0]?.id ?? "";

const summary = [
  { id: "stay", title: "체류기간 임박", value: `${urgentWorkers.length}건`, detail: `즉시 ${workers.filter((w) => w.statusTone === "red").length}, 우선 ${workers.filter((w) => w.statusTone === "orange").length}`, tone: "red" as Tone, icon: FileText, workerId: firstUrgentId },
  { id: "docs", title: "서류 보완 필요", value: `${docWorkers.length}건`, detail: `필수 ${docWorkers.length}, 선택 0`, tone: "orange" as Tone, icon: FileText, workerId: firstDocId },
  { id: "contract", title: "계약 종료 임박", value: `${workers.filter((w) => w.contractEnd && w.dday.startsWith("D-") && parseInt(w.dday.slice(2)) <= 30).length}건`, detail: "D-30 이내", tone: "blue" as Tone, icon: Clock3, workerId: firstUrgentId },
  { id: "approval", title: "승인 대기", value: `${riskCases.length}건`, detail: `담당자 검토 ${riskCases.length}건`, tone: "orange" as Tone, icon: Shield, workerId: firstUrgentId },
  { id: "admin", title: "행정사 검토 준비", value: "1건", detail: "초안 완료 1건", tone: "blue" as Tone, icon: FileText, workerId: workers.find((w) => w.statusTone === "red")?.id ?? workers[0]?.id ?? "" },
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
  const [selectedWorkerId, setSelectedWorkerId] = useState(workers[0]?.id ?? "");
  const [selectedSummaryId, setSelectedSummaryId] = useState("stay");
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
        <Card className={styles.briefing}>
          <div className={styles.row}>
            <span className={styles.gradientMark}>반</span>
            <div>
              <strong>오늘 브리핑이 준비되었습니다</strong>
              <p className={styles.subtle}>
                외고반장이 {totalRiskCaseCount}개 케이스를 정리했습니다. 즉시 확인 {workers.filter((w) => w.statusTone === "red").length}건, 우선 확인 {workers.filter((w) => w.statusTone === "orange").length}건, 승인 대기 {riskCases.length}건. 모든 판단의 근거는 항목 클릭으로 확인할 수 있습니다.
              </p>
            </div>
          </div>
          <div className={styles.buttonRow}>
            <span className={styles.subtle}>오늘 08:00</span>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "refresh", label: "다시 생성" })}>
              <RefreshCcw size={16} /> 다시 생성
            </Button>
          </div>
        </Card>

        <div className={styles.summaryGrid}>
          {summary.map((item) => (
            <button
              className={cn(styles.card, styles.statCard, styles.summaryButton, selectedSummaryId === item.id && styles.summaryButtonActive)}
              data-testid={`summary-${item.id}`}
              key={item.title}
              onClick={() => selectSummary(item)}
              type="button"
            >
              <div className={styles.sectionTitle}>
                <IconTile icon={item.icon} tone={item.tone} />
                <span className={styles.muted}>↗</span>
              </div>
              <div className={styles.subtle}>{item.title}</div>
              <div className={cn(styles.statValue, textToneClass(item.tone))}>{item.value}</div>
              <div className={styles.subtle}>{item.detail}</div>
            </button>
          ))}
        </div>

        <div className={styles.sectionTitle}>
          <div className={styles.buttonRow}>
            <Button>전체</Button>
            <Button variant="secondary">즉시 확인 <Badge tone="gray">{workers.filter((w) => w.statusTone === "red").length}</Badge></Button>
            <Button variant="secondary">우선 확인 <Badge tone="gray">{workers.filter((w) => w.statusTone === "orange").length}</Badge></Button>
            <Button variant="secondary">확인 필요 <Badge tone="gray">{workers.filter((w) => w.statusTone === "blue").length}</Badge></Button>
            <Button variant="secondary">참고 <Badge tone="gray">{workers.filter((w) => w.statusTone === "green").length}</Badge></Button>
          </div>
          <div className={styles.buttonRow}>
            <Button variant="secondary">전체 라인</Button>
            <Button variant="secondary">승인 대기만</Button>
            <Button variant="secondary">서류 보완 필요</Button>
          </div>
        </div>

        <Card className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>근로자</th>
                <th>국적·체류</th>
                <th>체류만료 / D-day</th>
                <th>계약 종료</th>
                <th>서류</th>
                <th>위험도 / 케이스</th>
                <th>다음 처리</th>
              </tr>
            </thead>
            <tbody>
              {[...workers].sort((a, b) => {
                const order = { red: 0, orange: 1, blue: 2, green: 3, gray: 4, purple: 5, teal: 6 };
                return (order[a.statusTone] ?? 9) - (order[b.statusTone] ?? 9);
              }).slice(0, 8).map((worker) => (
                <tr
                  className={selectedWorkerId === worker.id ? styles.selectedRow : undefined}
                  data-testid={workerTestId(worker.id)}
                  key={worker.id}
                  onClick={() => selectWorker(worker.id)}
                >
                  <td>
                    <div className={styles.row}>
                      <span className={styles.workerAvatar}>{worker.initials}</span>
                      <div>
                        <strong>{worker.name}</strong>
                        <span className={styles.muted}> · {worker.localName}</span>
                        <div className={styles.subtle}>{worker.line}</div>
                      </div>
                    </div>
                  </td>
                  <td><strong>{worker.nationalityCode} {worker.nationality}</strong><div className={styles.subtle}>{worker.visaType}</div></td>
                  <td><strong>{worker.visaExpiry}</strong><div className={cn(styles.subtle, worker.dday.includes("+") ? styles.textRed : styles.textOrange)}>{worker.dday}</div></td>
                  <td><strong>{worker.contractEnd}</strong><div className={styles.subtle}>{worker.dday}</div></td>
                  <td><div className={styles.buttonRow}>{worker.docs.map((doc) => <span className={styles.docChip} key={doc}>{doc}</span>)}{worker.docExtra && <strong className={styles.textOrange}>{worker.docExtra} 보완</strong>}</div></td>
                  <td><Badge tone={worker.statusTone}>{worker.status} · {worker.dday}</Badge><div className={styles.subtle}>{worker.status}</div></td>
                  <td>
                    <PillButton onClick={(event) => { event.stopPropagation(); selectWorker(worker.id); }}>
                      처리
                    </PillButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
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
  const isOverdue = worker.dday.startsWith("D+");
  const isUrgent = worker.statusTone === "red" || worker.statusTone === "orange";
  const hasMissingDoc = worker.docExtra != null;
  const risks = [
    ...(isOverdue ? [{
      title: "체류만료 초과",
      desc: `체류만료일(${worker.visaExpiry})이 지났습니다. 담당자 확인과 검토 자료 정리가 필요합니다.`,
      basis: ["출입국관리법 제25조", "제94조 벌칙"],
    }] : isUrgent ? [{
      title: "체류만료 임박",
      desc: `체류만료까지 ${worker.dday} 남았습니다. 연장 신청 또는 자진 출국 검토가 필요합니다.`,
      basis: ["출입국관리법 제25조", "체류기간 연장허가 신청 안내"],
    }] : [{
      title: "확인 필요",
      desc: "계약·체류·서류 상태를 담당자가 확인해야 합니다.",
      basis: ["근로자 프로필", "체류 정보"],
    }]),
    ...(hasMissingDoc ? [{
      title: "필수서류 누락",
      desc: `서류 보완이 필요합니다. (${worker.docExtra})`,
      basis: ["외국인근로자 고용 시 보유 서류"],
    }] : []),
  ];
  const docLabels: Record<string, string> = { 여: "여권사본", 외: "외국인등록증", 근: "근로계약서", 건: "건강진단서" };
  const allDocKeys = ["여", "외", "근", "건"];
  const docs: Array<[string, string, Tone]> = allDocKeys.map((key) => [
    docLabels[key] ?? key,
    worker.docs.includes(key) ? "확보됨" : "보완 필요",
    worker.docs.includes(key) ? "green" as Tone : "orange" as Tone,
  ]);

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
          <Card className={styles.panel}><div className={styles.subtle}>계약종료일</div><strong>{worker.contractEnd}</strong><div className={styles.subtle}>{worker.dday}</div></Card>
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
          {[`${workers.find((w) => w.statusTone === "red")?.name ?? workers[0]?.name} 케이스 승인 요청`, "오늘 브리핑 생성", `${worker.name} 리스크 플래그`, `CSV 업로드 — ${workers.length}명 동기화`].map((item, index) => (
            <div className={styles.row} key={item}><span className={cn(styles.dot, index === 0 ? styles.toneBlue : styles.toneGray)} /><div><strong>{item}</strong><div className={styles.subtle}>{index === 0 ? "08:14 · 김민수 차장" : index === 1 ? "08:01 · 시스템" : "08:00 · 시스템"}</div></div></div>
          ))}
        </div>
      </section>
    </aside>
  );
}

export function HiringPreparationView({ onAction }: PcViewProps = {}) {
  const hiringCards = [
    { title: "신규 E-9 3명 채용 준비", meta: "화성 1공장 · 조립라인 · 행정사 검토 전 확인 필요", deadline: "2026.05.20", percent: 72, done: "5/8 완료", tone: "teal" as Tone, tasks: ["구인노력 기간 확인", "고용허가 신청서 준비", "채용 요청서 확인"] },
    { title: "Candidate A 입국 전 서류 패키지", meta: "화성 1공장 · 도장라인 · 행정사 검토 전 확인 필요", deadline: "2026.05.20", percent: 45, done: "2/5 완료", tone: "orange" as Tone, tasks: ["건강진단서 원본 확인", "입국 전 교육 수료증 확인", "근로계약서 사본 확인"] },
  ];

  return (
    <div className={styles.stack}>
      <div>
        <h1 className={styles.headline}>채용 준비</h1>
        <p className={styles.subtle}>신규 고용 준비 상태를 점검합니다. 후보자 점수화나 추천은 하지 않습니다.</p>
      </div>
      <Card className={styles.briefing}>
        <span className={styles.gradientMark} />
        <div>
          <strong>신규 채용 준비 2건 진행 중</strong>
          <p className={styles.subtle}>검토 필요 1건 · 준비 중 1건</p>
        </div>
      </Card>
      {hiringCards.map((card) => (
        <Card className={styles.document} key={card.title}>
          <div className={styles.pageHead}>
            <div>
              <div className={styles.badgeLine}>
                <Badge>E-9 · 3명</Badge>
                <Badge tone={card.tone === "teal" ? "blue" : "orange"}>{card.tone === "teal" ? "준비 중" : "검토 필요"}</Badge>
              </div>
              <h2>{card.title}</h2>
              <p className={styles.subtle}>{card.meta}</p>
            </div>
            <div>
              <div className={styles.subtle}>마감</div>
              <strong>{card.deadline}</strong>
            </div>
          </div>
          <div>
            <div className={styles.sectionTitle}>
              <span>준비 완료도</span>
              <strong className={textToneClass(card.tone)}>{card.percent}%</strong>
            </div>
            <div className={styles.progressTrack}>
              <div className={styles.progressBar} style={{ width: `${card.percent}%` }} />
            </div>
            <p className={styles.subtle}>{card.done}</p>
          </div>
          <div className={styles.stack}>
            {card.tasks.map((task) => (
              <div className={cn(styles.row, styles.panel, styles.toneGray)} key={task}>
                <span className={styles.docChip} aria-hidden />
                <span>{task}</span>
              </div>
            ))}
          </div>
          <div className={styles.buttonRow}>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "handoff-preview", label: "요청서 보기" })}><FileText size={16} /> 요청서 보기</Button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "approval-preview", label: "행정사 검토 요청" })}><Check size={16} /> 행정사 검토 요청</Button>
            <span className={styles.subtle}>남은 작업 {card.tasks.length}개</span>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function WorkersView({ onAction }: PcViewProps = {}) {
  const statCards: Array<[string, string, Tone]> = [
    ["전체 등록", `${workers.length}명`, "blue"],
    ["즉시·우선 확인", `${urgentWorkers.length}명`, "orange"],
    ["서류 보완 필요", `${docWorkers.length}명`, "red"],
    ["정상", `${normalWorkers.length}명`, "green"],
  ];
  return (
    <div>
      <div className={styles.pageHead}>
        <div>
          <div className={styles.subtle}>근로자 목록</div>
          <h1 className={styles.headline}>{company.name} · {workers.length}명</h1>
        </div>
        <Button variant="secondary" onClick={() => onAction?.({ kind: "worker-register", label: "근로자 등록" })}>+ 근로자 등록</Button>
      </div>
      <div className={styles.metricGrid}>
        {statCards.map(([title, value, tone]) => (
          <Card className={styles.panel} key={title}>
            <div className={styles.subtle}>{title}</div>
            <div className={cn(styles.statValue, textToneClass(tone))}>{value}</div>
          </Card>
        ))}
      </div>
      <Card className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr><th>근로자</th><th>국적·체류</th><th>체류만료 / D-day</th><th>계약 종료</th><th>서류 현황</th><th>위험도</th><th>근속</th></tr>
          </thead>
          <tbody>
            {workers.map((worker) => (
              <tr key={worker.id}>
                <td>
                  <div className={styles.row}>
                    <span className={styles.workerAvatar}>{worker.initials}</span>
                    <div><strong>{worker.name} <span className={styles.muted}>{worker.localName}</span></strong><div className={styles.subtle}>{worker.line}</div></div>
                  </div>
                </td>
                <td><strong>{worker.nationalityCode} {worker.nationality}</strong><div className={styles.subtle}>{worker.visaType}</div></td>
                <td><strong>{worker.visaExpiry}</strong><div className={cn(styles.subtle, worker.dday.includes("+") ? styles.textRed : styles.textBlue)}>{worker.dday}</div></td>
                <td><strong>{worker.contractEnd}</strong><div className={styles.subtle}>{worker.dday}</div></td>
                <td><div className={styles.buttonRow}>{worker.docs.map((doc) => <span className={styles.docChip} key={doc}>{doc}</span>)}{worker.docExtra && <strong className={styles.textOrange}>{worker.docExtra}</strong>}</div></td>
                <td><Badge tone={worker.statusTone}>{worker.status}</Badge></td>
                <td>{worker.tenure}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export function CasesView({ onAction }: PcViewProps = {}) {
  const groups = ["즉시 확인", "우선 확인", "확인 필요"];
  return (
    <div className={styles.stack}>
      <div>
        <div className={styles.subtle}>케이스 목록</div>
        <h1 className={styles.headline}>리스크 케이스 · {totalRiskCaseCount}건</h1>
        <p className={styles.subtle}>AI는 비자 가능 여부를 확정하지 않으며, 담당자 검토용 근거와 초안만 제공합니다.</p>
      </div>
      {groups.map((group) => {
        const items = riskCases.filter((item) => item.group === group);
        if (!items.length) return null;
        const groupTone = items[0].tone;
        return (
          <section className={styles.caseGroup} key={group}>
            <div className={styles.titleLine}>
              <span className={cn(styles.dot, toneClass(groupTone))} />
              <strong>{group}</strong>
              <Badge tone="gray">{items.length}건</Badge>
            </div>
            {items.map((item) => (
              <Card className={cn(styles.caseCard, item.tone === "red" ? styles.caseRed : item.tone === "orange" ? styles.caseOrange : styles.caseBlue)} key={item.id}>
                <div className={styles.pageHead}>
                  <div>
                    <div className={styles.badgeLine}>
                      <Badge tone={item.tone}>{group}</Badge>
                      <h2>{item.title}</h2>
                      {item.nationalityCode && <Badge tone="purple">{item.nationalityCode}</Badge>}
                      <strong className={styles.muted}>{item.worker}</strong>
                    </div>
                    <p>{item.desc}</p>
                    <div className={styles.buttonRow}>
                      {item.actions.map((action) => (
                        <PillButton
                          key={action}
                          onClick={() =>
                            onAction?.({
                              kind: action.includes("초안")
                                ? "document-draft"
                                : action.includes("자료") || action.includes("신고서")
                                  ? "handoff-preview"
                                  : "response-summary",
                              label: action,
                            })
                          }
                        >
                          {action}
                        </PillButton>
                      ))}
                    </div>
                  </div>
                  <span className={styles.subtle}>{item.id}</span>
                </div>
              </Card>
            ))}
          </section>
        );
      })}
    </div>
  );
}

export function ContactView({ onAction }: PcViewProps = {}) {
  return (
    <div>
      <div className={styles.pageHead}>
        <div>
          <h1 className={styles.headline}>메시지 관리</h1>
          <p className={styles.subtle}>근로자별 다국어 컨택 초안을 확인하고 승인합니다.</p>
        </div>
      </div>
      <Card className={styles.contactLayout}>
        <aside className={styles.contactList}>
          <div className={styles.panel}>컨택 목록 · 3건</div>
          {contactItems.map((item, index) => (
            <div className={cn(styles.contactItem, index === 0 && styles.contactSelected)} key={item.worker}>
              <span className={styles.workerAvatar}>{item.initials}</span>
              <div>
                <div className={styles.badgeLine}><strong>{item.worker}</strong><span>{item.country}</span><Badge>{item.badge}</Badge></div>
                <div className={styles.subtle}>{item.desc}</div>
                <div className={styles.badgeLine}><Badge tone={item.status === "응답 도착" ? "green" : item.status === "승인 대기" ? "orange" : "gray"}>{item.status}</Badge><span className={styles.subtle}>{item.date}</span></div>
              </div>
            </div>
          ))}
        </aside>
        <section>
          <div className={styles.document}>
            <div className={styles.pageHead}>
              <div><div className={styles.titleLine}><strong>VN</strong><h2>Nguyen V.</h2></div><p className={styles.subtle}>베트남 · Zalo · 응우엔 V.</p></div>
              <Badge tone="gray">초안</Badge>
            </div>
            <div className={styles.draftNotice}>승인 전에는 외부로 발송되지 않습니다. 담당자 검토용 초안입니다.</div>
          </div>
          <div className={styles.document}>
            <div className={styles.buttonRow}><Button variant="ghost">Tiếng Việt</Button><Button variant="ghost">한국어</Button></div>
            <div className={styles.messageBox}>
              Xin chào anh Nguyen V.,<br /><br />Đây là Oegobanjang.<br />Chúng tôi đang chuẩn bị gia hạn thời gian cư trú.<br />Vui lòng gửi các giấy tờ sau trước ngày 20 tháng 5.<br /><br />1. Bản sao hộ chiếu (trang ảnh)<br />2. Bản sao thẻ đăng ký người nước ngoài (mặt trước & mặt sau)<br /><br />Mục đích thu thập: Chuẩn bị hồ sơ gia hạn cư trú.<br />Thời gian lưu giữ: 30 ngày sau khi nộp hồ sơ.
            </div>
            <h3>예상 응답 시나리오</h3>
            <div className={styles.scenarioGrid}>
              <Scenario title="긍정 응답" desc="서류 수신 후 반영 후보 생성 / 담당자 확인 후 반영" tone="green" />
              <Scenario title="추가 정보 요청" desc="필요 서류와 형식 기준을 다시 안내" tone="blue" />
              <Scenario title="응답 지연" desc="2일 뒤 리마인드 메시지 제안" tone="orange" />
            </div>
          </div>
          <div className={cn(styles.buttonRow, styles.document)}>
            <Button variant="ghost" onClick={() => onAction?.({ kind: "response-summary", label: "나중에 보기" })}>나중에 보기</Button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "revision-request", label: "수정 요청" })}>수정 요청</Button>
            <Button onClick={() => onAction?.({ kind: "approval-preview", label: "승인" })}>승인</Button>
          </div>
        </section>
      </Card>
    </div>
  );
}

export function AdminReviewView({ onAction }: PcViewProps = {}) {
  return (
    <div className={styles.split}>
      <Card className={styles.document}>
        <div className={styles.pageHead}>
          <div>
            <div className={styles.subtle}>행정사 검토용 자료 · 초안</div>
            <h1 className={styles.headline}>{adminPackage.title}</h1>
            <p className={styles.subtle}>생성 {adminPackage.createdAt} · 수신자 {adminPackage.receiver} (검토 대기)</p>
          </div>
          <Badge tone="orange">{adminPackage.status}</Badge>
        </div>
        <InfoTable title="근로자 기본 정보" rows={adminPackage.profile} />
        <InfoTable title="체류 / 계약 상태" rows={adminPackage.stay} />
        <InfoTable title="제출 서류" rows={adminPackage.docs} />
      </Card>
      <aside className={styles.sideStack}>
        <Card className={styles.panel}>
          <h2>다음 단계</h2>
          <div className={styles.stack}>
            <Button onClick={() => onAction?.({ kind: "approval-preview", label: "승인 후 검토 자료 확정" })}>승인 후 검토 자료 확정</Button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "revision-request", label: "수정 요청" })}>수정 요청</Button>
            <Button variant="ghost" onClick={() => onAction?.({ kind: "pdf-draft", label: "PDF 내보내기" })}><Download size={16} /> PDF 내보내기</Button>
          </div>
          <p className={styles.subtle}>승인 후에도 정부 포털 자동 제출은 수행하지 않습니다.</p>
        </Card>
        <Card className={styles.panel}>
          <h2>포함된 근거 (3)</h2>
          <Evidence source="국가법령정보센터" text="출입국관리법 제25조 (체류기간 연장허가)" grade="A" />
          <Evidence source="출입국관리법" text="제94조 벌칙 (체류기간 초과)" grade="A" />
          <Evidence source="HiKorea" text="체류기간 연장허가 신청 안내" grade="B" />
        </Card>
        <Card className={styles.panel}>
          <h2>승인 흐름</h2>
          {["시스템 초안 생성", "담당자 검토", "사장님 승인", "행정사 전달 준비"].map((step, index) => (
            <div className={styles.row} key={step}><Badge tone={index < 2 ? "green" : "gray"}>{index + 1}</Badge><strong>{step}</strong></div>
          ))}
        </Card>
      </aside>
    </div>
  );
}

export function JudgmentLogView({ onAction }: PcViewProps = {}) {
  return (
    <div className={styles.judgmentLayout}>
      <section className={styles.judgmentList}>
        <h1 className={styles.headline}>판단 기록</h1>
        <div className={styles.buttonRow}><Button>전체</Button><Button variant="secondary">승인 필요</Button><Button variant="secondary">발송 예정</Button><Button variant="secondary">행정사 검토</Button></div>
        <div className={styles.buttonRow}><div className={cn(styles.button, styles.buttonGhost)}><Search size={16} /> 키워드 검색 (사유, 이벤트, 대상 등)</div><Button variant="secondary">필터</Button></div>
        <Card className={styles.tableWrap}>
          <table className={styles.table}>
            <thead><tr><th><input type="checkbox" aria-label="판단 기록 전체 선택" /></th><th>판단 기록</th><th>대상 근로자</th><th>최종 상태</th><th>판단일</th></tr></thead>
            <tbody>{judgmentRows.map((row, index) => <tr className={index === 0 ? styles.selectedRow : undefined} key={row.id}><td><input type="checkbox" aria-label={`${row.id} 선택`} /></td><td><strong className={styles.textBlue}>{row.id}</strong></td><td>{row.worker}</td><td><Badge tone={row.tone}>{row.status}</Badge></td><td>{row.date}</td></tr>)}</tbody>
          </table>
        </Card>
      </section>
      <aside className={styles.judgmentDetail}>
        <div className={styles.pageHead}><h2>판단 기록 #4789 <Badge tone="green">승인 완료</Badge></h2><div className={styles.buttonRow}><Button variant="secondary" onClick={() => onAction?.({ kind: "response-summary", label: "판단 기록 메뉴" })}><MoreHorizontal size={16} /></Button><Button variant="ghost" onClick={() => onAction?.({ kind: "response-summary", label: "상세 닫기" })}><X size={16} /></Button></div></div>
        <div className={styles.infoGrid}><Info label="담당자" value="김대리 (인사팀)" /><Info label="대상 근로자" value="Nguyen V." /><Info label="관련 케이스" value="체류기간 연장 서류 요청" /></div>
        <div className={styles.separator} />
        <Block title="판단 요약"><Card className={styles.panel}>체류만료일이 45일 이내로 확인되어, 누락된 서류 요청 초안을 만들고 실제 전달 전 대표 승인이 완료됐습니다.</Card></Block>
        <Block title="사용한 정보"><div className={styles.badgeLine}><Badge tone="gray">근로자 프로필</Badge><Badge tone="gray">체류 정보</Badge><Badge tone="gray">케이스 정보</Badge><Badge tone="gray">이전 대화 기록</Badge><Badge tone="gray">서류 체크리스트</Badge></div></Block>
        <Block title="승인 이력"><Card className={styles.panel}><div className={styles.sectionTitle}><div><strong>대표 (서류 요청 초안)</strong><p className={styles.subtle}>김대표 · 2026-05-21 10:42</p></div><Badge tone="green">승인 완료</Badge></div></Card></Block>
        <Block title="이벤트 타임라인"><Timeline /></Block>
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
