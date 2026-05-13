import {
  Check,
  CheckCircle,
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
import { adminPackage, contactItems, judgmentRows, riskCases, workers, type Tone } from "./data";
import { Badge, Button, Card, cn, IconTile, PillButton, textToneClass, toneClass } from "./ui";
import styles from "./PcShell.module.css";
import type { DailyBriefingItem, DailyBriefingResult, NextAction } from "../../types/dailyBriefing";

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
  actionId?: string;
  kind: PcActionKind;
  label: string;
};

export type PcViewProps = {
  briefing?: DailyBriefingResult | null;
  loading?: boolean;
  onAction?: (action: PcViewAction) => void;
};

const statusLabel: Record<NextAction["status"], string> = {
  approved: "승인됨",
  blocked: "차단",
  cancelled: "취소",
  completed: "완료",
  pending_approval: "승인 대기",
  rejected: "반려",
  revision_requested: "수정 요청",
};

const riskTypeLabel: Record<DailyBriefingItem["risk_type"], string> = {
  candidate_readiness: "후보자 입국 전 서류",
  contract_visa_conflict: "계약 종료 확인",
  missing_document: "서류 보완 필요",
  quota_review: "신규 채용 준비",
  reporting_deadline: "고용변동 신고기한",
  visa_expiry: "체류기간 연장 서류",
};

const riskIconByType: Record<DailyBriefingItem["risk_type"], typeof FileText> = {
  candidate_readiness: FileText,
  contract_visa_conflict: MessageSquare,
  missing_document: FileText,
  quota_review: UserRoundPlus,
  reporting_deadline: Shield,
  visa_expiry: FileText,
};

function severityTone(item: DailyBriefingItem): Tone {
  if (item.severity === "CRITICAL") return "red";
  if (item.severity === "HIGH") return "orange";
  if (item.severity === "MEDIUM") return "blue";
  return "green";
}

function timingLabel(item: DailyBriefingItem) {
  if (item.risk_timing_label) return item.risk_timing_label;
  if (item.expired) return `D+${item.days_overdue ?? 0}`;
  if (item.d_day !== null) return `D-${item.d_day}`;
  return "이번 주";
}

function rowStatus(actions: NextAction[]) {
  const primary = actions[0];
  if (!primary) return "확인 필요";
  return statusLabel[primary.status] ?? primary.status;
}

function nextActionLabel(actions: NextAction[]) {
  const action = actions[0];
  if (!action) return "근거 보기";
  if (action.action_type === "request_document") return "초안 보기";
  return "검토 자료 보기";
}

function nextActionKind(actions: NextAction[]): PcActionKind {
  const action = actions[0];
  if (!action) return "response-summary";
  if (action.action_type === "request_document") return "document-draft";
  if (action.status === "pending_approval") return "approval-preview";
  return "handoff-preview";
}

function buildLiveSummary(briefing: DailyBriefingResult | null) {
  const items = briefing?.items ?? [];
  const actions = briefing?.recommended_actions ?? [];
  const byRisk = (riskType: DailyBriefingItem["risk_type"]) => items.filter((item) => item.risk_type === riskType).length;
  return [
    { title: "체류기간 임박", value: `${byRisk("visa_expiry")}명`, tone: "red" as Tone, icon: FileText },
    { title: "서류 보완 필요", value: `${byRisk("missing_document")}건`, tone: "orange" as Tone, icon: FileText },
    { title: "신규 채용 준비", value: `${byRisk("quota_review")}건`, tone: "green" as Tone, icon: UserRoundPlus },
    { title: "컨택 대기", value: `${actions.filter((action) => action.action_type === "request_document").length}건`, tone: "purple" as Tone, icon: MessageSquare },
    { title: "응답 도착", value: `${byRisk("contract_visa_conflict")}건`, tone: "blue" as Tone, icon: MessageSquare },
    { title: "승인 대기", value: `${actions.filter((action) => action.status === "pending_approval").length}건`, tone: "orange" as Tone, icon: Shield },
    { title: "행정사 검토 준비", value: `${actions.filter((action) => action.action_type === "create_handoff").length}건`, tone: "blue" as Tone, icon: FileText },
  ];
}

export function TodayTasksView({ briefing = null, loading = false, onAction }: PcViewProps = {}) {
  const liveSummary = buildLiveSummary(briefing);
  const liveItems = briefing?.items ?? [];
  const liveActions = briefing?.recommended_actions ?? [];
  const visibleItems = liveItems.slice(0, 8);
  const pendingCount = liveActions.filter((action) => action.status === "pending_approval").length;

  return (
    <div className={styles.stack}>
      <Card className={styles.briefing}>
        <div className={styles.row}>
          <span className={styles.gradientMark}>반</span>
          <div>
            <strong>오늘 브리핑이 준비되었습니다</strong>
            <p className={styles.subtle}>
              외고반장이 {liveItems.length}개 케이스를 정리했습니다. 즉시 확인{" "}
              {briefing?.risk_summary.critical_count ?? 0}건, 우선 확인 {briefing?.risk_summary.high_count ?? 0}건,
              승인 대기 {pendingCount}건.
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
        {liveSummary.map((item) => (
          <Card className={styles.statCard} key={item.title}>
            <IconTile icon={item.icon} tone={item.tone} />
            <div className={styles.subtle}>{item.title}</div>
            <div className={cn(styles.statValue, textToneClass(item.tone))}>{item.value}</div>
          </Card>
        ))}
      </div>

      <section>
        <div className={styles.sectionTitle}>
          <h1 className={styles.headline}>오늘의 업무 큐 <Badge>{visibleItems.length}건</Badge></h1>
          <div className={styles.buttonRow}>
            <Button variant="secondary">필터</Button>
            <Button variant="secondary">기한 임박 순</Button>
          </div>
        </div>
        <Card className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th><input type="checkbox" aria-label="전체 선택" /></th>
                <th>업무</th>
                <th>대상</th>
                <th>상태</th>
                <th>기한</th>
                <th>다음 처리</th>
                <th aria-label="더보기" />
              </tr>
            </thead>
            <tbody>
              {loading && !briefing ? (
                <tr>
                  <td colSpan={7}>브리핑 데이터를 불러오는 중입니다.</td>
                </tr>
              ) : null}
              {!loading && !visibleItems.length ? (
                <tr>
                  <td colSpan={7}>오늘 표시할 원본 브리핑 업무가 없습니다.</td>
                </tr>
              ) : null}
              {visibleItems.map((item) => {
                const rowActions = liveActions.filter((action) => item.next_action_ids.includes(action.action_id));
                const primaryAction = rowActions[0];
                const tone = severityTone(item);
                const Icon = riskIconByType[item.risk_type];
                return (
                <tr key={item.item_id}>
                  <td><input type="checkbox" aria-label={`${item.case_title ?? item.item_id} 선택`} /></td>
                  <td>
                    <div className={styles.row}>
                      <IconTile icon={Icon} tone={tone} />
                      <strong>{item.case_title ?? riskTypeLabel[item.risk_type]}</strong>
                    </div>
                  </td>
                  <td>{item.subject_display_name ?? item.subject_display_id ?? item.subject_id}</td>
                  <td><Badge tone={tone}>{rowStatus(rowActions)}</Badge></td>
                  <td><strong>{timingLabel(item)}</strong></td>
                  <td>
                    <PillButton
                      onClick={() =>
                        onAction?.({
                          actionId: primaryAction?.action_id,
                          kind: nextActionKind(rowActions),
                          label: nextActionLabel(rowActions),
                        })
                      }
                    >
                      {nextActionLabel(rowActions)}
                    </PillButton>
                  </td>
                  <td>⋮</td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      </section>
    </div>
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
    ["전체 등록", "6명", "blue"],
    ["즉시·우선 확인", "2명", "orange"],
    ["서류 보완 필요", "3명", "red"],
    ["정상", "1명", "green"],
  ];
  return (
    <div>
      <div className={styles.pageHead}>
        <div>
          <div className={styles.subtle}>근로자 목록</div>
          <h1 className={styles.headline}>한별제조 · 6명</h1>
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
