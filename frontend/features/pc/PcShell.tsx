"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BriefcaseBusiness,
  CalendarCheck,
  Clock3,
  LogOut,
  MessageSquare,
  Search,
  UserRoundPlus,
  Users,
} from "lucide-react";
import { company, type PcViewKey } from "./data";
import { cn } from "./ui";
import styles from "./PcShell.module.css";
import {
  CasesView,
  ContactView,
  HiringPreparationView,
  JudgmentLogView,
  TodayTasksView,
  WorkersView,
  type PcViewAction,
} from "./views";
import type { DailyBriefingItem, DailyBriefingResult, NextAction } from "../../types/dailyBriefing";
import { DailyBriefingChatPanel } from "../dashboard/DailyBriefingChatPanel";
import { useDailyBriefingWorkflow } from "../dashboard/useDailyBriefingWorkflow";
import { clearOperatorContext, getOperatorContext, type OperatorContext } from "../../lib/operatorContext";
import { type AgentReviewResult, type ActionContactThread, runAgentReview, getActionContactThreads } from "../../lib/api";

const DOC_CODE_TO_KO: Record<string, string> = {
  work_permit: "고용허가서 사본",
  alien_registration: "외국인등록증 사본",
  employment_contract: "표준근로계약서",
  labor_contract: "표준근로계약서",
  passport_copy: "여권 사본",
  passport: "여권 사본",
  health_certificate: "건강검진 결과서",
  criminal_record: "범죄경력 조회서",
  standard_contract: "표준근로계약서",
};

function docCodeToKo(code: string): string {
  return DOC_CODE_TO_KO[code.toLowerCase()] ?? code;
}

const RISK_TYPE_TITLE: Record<string, string> = {
  visa_expiry: "체류기간 연장 검토 요청서",
  contract_visa_conflict: "계약·체류 충돌 검토 요청서",
  missing_document: "서류 보완 요청서",
  candidate_readiness: "채용 후보자 검토 요청서",
};

const routes: Array<{ key: PcViewKey; href: string; label: string; icon: React.ElementType }> = [
  { key: "today", href: "/dashboard", label: "오늘 할 일", icon: CalendarCheck },
  { key: "hiring", href: "/hiring", label: "채용 준비", icon: UserRoundPlus },
  { key: "workers", href: "/workers", label: "근로자", icon: Users },
  { key: "contact", href: "/contacts", label: "메시지 관리", icon: MessageSquare },
  { key: "judgment", href: "/evidence", label: "판단 기록", icon: Clock3 },
];

const pathToView: Record<string, PcViewKey> = {
  "/dashboard": "today",
  "/hiring": "hiring",
  "/workers": "workers",
  "/contacts": "contact",
  "/visa": "cases",
  "/evidence": "judgment",
};

const viewToPath: Partial<Record<PcViewKey, string>> = {
  contact: "/contacts",
  hiring: "/hiring",
};

function renderView(
  view: PcViewKey,
  onAction: (action: PcViewAction) => void,
  briefing: DailyBriefingResult | null,
  loading: boolean,
  onNavigateToMessages?: (threadId: string, tab?: "worker" | "expert") => void,
) {
  if (view === "hiring") return <HiringPreparationView onAction={onAction} />;
  if (view === "workers") return <WorkersView onAction={onAction} />;
  if (view === "contact") return <ContactView onAction={onAction} />;
  if (view === "cases") return <CasesView onAction={onAction} briefing={briefing} />;
  if (view === "judgment") return <JudgmentLogView onAction={onAction} briefing={briefing} />;
  return <TodayTasksView briefing={briefing} loading={loading} onAction={onAction} onNavigateToMessages={onNavigateToMessages} />;
}

type InfoPanel = {
  title: string;
  body: React.ReactNode;
};

export function PcShell({
  activeViewOverride,
  children,
}: {
  activeViewOverride?: PcViewKey;
  children?: React.ReactNode;
} = {}) {
  const pathname = usePathname();
  const router = useRouter();
  const activeView = activeViewOverride ?? pathToView[pathname] ?? "today";
  const workflow = useDailyBriefingWorkflow();
  const [chatOpen, setChatOpen] = useState(false);
  const [panel, setPanel] = useState<InfoPanel | null>(null);
  const [operator, setOperator] = useState<OperatorContext | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [workerRegisterOpen, setWorkerRegisterOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [chatSessionKey, setChatSessionKey] = useState(0);

  useEffect(() => {
    if (operator?.accessToken) {
      void workflow.runBriefing();
    }
  }, [operator?.accessToken, workflow.runBriefing]);

  useEffect(() => {
    const refreshBriefing = () => {
      void workflow.runBriefing();
    };
    window.addEventListener("workbridge-daily-briefing-refresh", refreshBriefing);
    return () => window.removeEventListener("workbridge-daily-briefing-refresh", refreshBriefing);
  }, [workflow.runBriefing]);

  useEffect(() => {
    const refreshOperator = () => {
      setOperator(getOperatorContext());
      setAuthReady(true);
    };
    refreshOperator();
    window.addEventListener("workbridge-operator-context-change", refreshOperator);
    return () => window.removeEventListener("workbridge-operator-context-change", refreshOperator);
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("ai") === "1") {
      setChatOpen(true);
    }
  }, []);

  const actions = workflow.briefing?.recommended_actions ?? [];
  const documentAction = useMemo(() => findAction(actions, "request_document"), [actions]);
  const handoffAction = useMemo(() => findAction(actions, "create_handoff"), [actions]);
  const pendingAction = useMemo(
    () => actions.find((action) => action.status === "pending_approval") ?? documentAction ?? handoffAction,
    [actions, documentAction, handoffAction],
  );

  async function openDocumentDraft(action?: NextAction | null) {
    if (action) {
      await workflow.openDocumentDraft(action);
      return;
    }
    setPanel({
      title: "서류 요청 초안",
      body: (
        <div className={styles.modalStack}>
          <p>화면 기준 서류 요청 초안 미리보기입니다. 실제 발송은 수행하지 않습니다.</p>
          <div className={styles.previewBox}>
            <strong>Tiếng Việt</strong>
            <p>
              Xin chào anh Nguyen V.,
              <br />
              Đây là Oegobanjang.
              <br />
              Chúng tôi đang chuẩn bị gia hạn thời gian cư trú.
              <br />
              Vui lòng gửi bản sao hộ chiếu và bản sao thẻ đăng ký người nước ngoài trước ngày 20 tháng 5.
            </p>
            <strong>KR</strong>
            <p>안녕하세요 Nguyen 씨, 체류기간 연장 준비를 위해 여권 사본과 외국인등록증 사본을 보내주세요.</p>
          </div>
        </div>
      ),
    });
  }

  async function openHandoffPreview(action?: NextAction | null) {
    const briefingItem = action
      ? (workflow.briefing?.items?.find((i) => i.case_id === action.case_id) ?? null)
      : null;
    const documentActionForWorker = action
      ? (actions.find((a) => a.subject_id === action.subject_id && a.action_type === "request_document") ?? documentAction)
      : documentAction;
    setPanel({
      title: "행정사 검토 자료",
      body: (
        <HandoffReadablePreview
          action={action ?? null}
          briefingItem={briefingItem}
          companyId={workflow.companyId}
          workflow={workflow}
          documentAction={documentActionForWorker ?? null}
          onClose={() => setPanel(null)}
        />
      ),
    });
  }

  async function approvePreview(action?: NextAction | null) {
    if (action?.status === "pending_approval") {
      const result = await workflow.approve(action);
      setPanel({
        title: "승인 처리 결과",
        body: (
          <div className={styles.modalStack}>
            <p>{result ? `승인 상태가 ${result.status}로 반영됐습니다.` : "승인 요청 처리 중 오류가 발생했습니다."}</p>
            <p>외부 발송은 자동 실행하지 않고, 담당자 확인 대기 상태만 표시합니다.</p>
          </div>
        ),
      });
      return;
    }
    setPanel({
      title: "승인 전 미리보기",
      body: (
        <div className={styles.modalStack}>
          <p>대표 승인 전 확인 화면입니다. 현재 화면에서는 실제 발송이나 외부 제출을 수행하지 않습니다.</p>
          <p>백엔드 승인 action이 준비되면 동일 버튼에서 승인 API를 호출합니다.</p>
        </div>
      ),
    });
  }

  async function requestRevision(action?: NextAction | null) {
    if (action?.status === "pending_approval") {
      await workflow.requestActionRevision(action, "PC dashboard에서 수정 요청");
    }
    setPanel({
      title: "수정 요청",
      body: <p>수정 요청 상태를 남겼습니다. 실제 외부 발송은 수행하지 않았습니다.</p>,
    });
  }

  async function handleAction(action: PcViewAction) {
    if (action.source === "today_queue" && action.targetView) {
      const targetPath = viewToPath[action.targetView];
      if (targetPath) {
        const params = new URLSearchParams();
        params.set("from", "today");
        params.set("action", action.kind);
        params.set("label", action.label);
        if (action.subjectId) params.set("worker_id", action.subjectId);
        if (action.subjectName) params.set("worker", action.subjectName);
        if (action.riskType) params.set("risk_type", action.riskType);
        router.push(`${targetPath}?${params.toString()}`);
        return;
      }
    }
    if (action.kind === "open-ai") {
      setChatSessionKey((value) => value + 1);
      setChatOpen(true);
      return;
    }
    if (action.kind === "refresh") {
      await workflow.runBriefing();
      setPanel({ title: "브리핑 다시 생성", body: <p>데일리 브리핑 데이터를 다시 요청했습니다.</p> });
      return;
    }
    if (action.kind === "document-draft") {
      await openDocumentDraft(documentAction);
      return;
    }
    if (action.kind === "handoff-preview") {
      const targetAction = action.subjectId
        ? (actions.find((a) => a.subject_id === action.subjectId && a.action_type === "create_handoff") ?? handoffAction)
        : handoffAction;
      await openHandoffPreview(targetAction);
      return;
    }
    if (action.kind === "approval-preview") {
      await approvePreview(pendingAction);
      return;
    }
    if (action.kind === "revision-request") {
      await requestRevision(pendingAction);
      return;
    }
    if (action.kind === "pdf-draft") {
      setPanel({
        title: "PDF 내보내기 초안",
        body: <p>대외 제출용 export는 승인 대상입니다. 여기서는 PDF 초안 생성 가능 상태만 표시합니다.</p>,
      });
      return;
    }
    if (action.kind === "worker-register") {
      setWorkerRegisterOpen(true);
      return;
    }
    setPanel({
      title: action.label,
      body: <p>응답 요약과 이전 대화 기록을 확인하는 검토용 화면입니다.</p>,
    });
  }

  function logout() {
    clearOperatorContext();
    router.push("/login");
  }

  function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;
    const lower = query.toLowerCase();
    if (activeView === "contact" || query.includes("메시지") || query.includes("행정사") || query.includes("답변") || lower.includes("message")) {
      router.push(`/contacts?search=${encodeURIComponent(query)}`);
      return;
    }
    if (query.includes("서류") || lower.includes("document") || query.includes("여권")) {
      router.push(`/workers?search=${encodeURIComponent(query)}`);
      return;
    }
    router.push(`/workers?search=${encodeURIComponent(query)}`);
  }

  const isLoggedIn = Boolean(operator?.accessToken);
  const displayName = operator?.displayName || company.manager;
  const displayRole = operator?.role === "worker" ? "근로자" : "관리자";

  if (!authReady) {
    return <div className={styles.shell} />;
  }

  if (!isLoggedIn) {
    return (
      <div className={styles.shell}>
        <header className={styles.header}>
          <div className={styles.topbar}>
            <Link className={styles.brand} href="/" aria-label="외고반장 홈">
              <span className={styles.brandMark}>반</span>
              <span className={styles.brandName}>외고반장</span>
            </Link>
            <Link className={styles.loginButton} href="/login">
              로그인
            </Link>
          </div>
        </header>
        <main className={styles.loginRequiredMain}>
          <section className={styles.loginRequiredCard}>
            <span className={styles.brandMark}>반</span>
            <h1>외고반장</h1>
            <p>로그인 후 사용 가능합니다.</p>
            <Link className={styles.loginRequiredButton} href="/login">
              로그인
            </Link>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.topbar}>
          <div className={styles.leftCluster}>
            <Link className={styles.brand} href="/dashboard" aria-label="외고반장 대시보드">
              <span className={styles.brandMark}>반</span>
              <span className={styles.brandName}>외고반장</span>
            </Link>
            <span className={styles.divider} aria-hidden />
            <button className={styles.company} type="button">
              <span className={styles.companyMark}>한</span>
              {company.name}
              <span className={styles.muted}>· {company.location}</span>
            </button>
          </div>

          <form className={styles.search} onSubmit={submitSearch} aria-label="검색">
            <Search size={16} />
            <input
              aria-label="검색"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="검색"
              value={searchQuery}
            />
          </form>

          <div className={styles.rightCluster}>
            {isLoggedIn ? (
              <>
                <div className={styles.person}>
                  <span className={styles.avatar}>{displayName.slice(0, 1)}</span>
                  <span>
                    <span className={styles.manager}>{displayName}</span>
                    <span className={styles.role}>{displayRole}</span>
                  </span>
                </div>
                <button className={styles.loginButton} onClick={logout} type="button">
                  <LogOut size={14} /> 로그아웃
                </button>
              </>
            ) : (
              <Link className={styles.loginButton} href="/login">
                로그인
              </Link>
            )}
          </div>
        </div>

        <nav className={styles.nav} aria-label="PC 주요 메뉴">
          {routes.map(({ key, href, label, icon: Icon }) => (
            <Link
              key={key}
              className={cn(styles.navItem, activeView === key && styles.navItemActive)}
              href={href}
              aria-current={activeView === key ? "page" : undefined}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </nav>
      </header>

      <main className={styles.main}>
        {children ?? renderView(activeView, (action) => void handleAction(action), workflow.briefing, workflow.loading, (threadId, tab) => {
          const params = new URLSearchParams();
          params.set("thread_id", threadId);
          if (tab === "expert") params.set("tab", "expert");
          router.push(`/contacts?${params.toString()}`);
        })}
      </main>

      <button
        className={styles.fab}
        data-testid="ai-fab"
        onClick={() => {
          setChatSessionKey((value) => value + 1);
          setChatOpen(true);
        }}
        type="button"
      >
        <BriefcaseBusiness size={16} /> AI 반장
      </button>

      {workflow.error ? (
        <div className={styles.toast} role="status">
          API 연결 상태: {workflow.error}
        </div>
      ) : null}

      {workflow.documentDraft ? (
        <PcDrawer title="서류 요청 메시지 초안" onClose={() => workflow.setDocumentDraft(null)}>
          <div className={styles.modalStack}>
            <h4>한국어</h4>
            <p>{workflow.documentDraft.korean_text}</p>
            <h4>번역 초안</h4>
            <p>{workflow.documentDraft.translated_text}</p>
            <p className={styles.safeNotice}>승인 전에는 외부로 발송되지 않습니다.</p>
          </div>
        </PcDrawer>
      ) : null}

      {workflow.preview ? (
        <PcDrawer title="행정사 검토 자료 미리보기" onClose={() => workflow.setPreview(null)}>
          <HandoffReadablePreview
            action={handoffAction}
            briefingItem={workflow.briefing?.items?.find((i) => i.case_id === handoffAction?.case_id) ?? null}
            companyId={workflow.companyId}
            workflow={workflow}
            documentAction={documentAction}
            onClose={() => workflow.setPreview(null)}
          />
        </PcDrawer>
      ) : null}

      {panel ? (
        <PcDrawer title={panel.title} onClose={() => setPanel(null)}>
          {panel.body}
        </PcDrawer>
      ) : null}

      {workerRegisterOpen ? (
        <WorkerRegisterDrawer
          companyId={operator?.companyId || workflow.companyId}
          onClose={() => setWorkerRegisterOpen(false)}
        />
      ) : null}

      {chatOpen ? (
        <div className={styles.drawerOverlay}>
          <button className={styles.drawerBackdrop} aria-label="AI 반장 닫기" onClick={() => setChatOpen(false)} type="button" />
          <aside className={styles.chatDrawer}>
            <button className={styles.closeButton} onClick={() => setChatOpen(false)} type="button">
              닫기
            </button>
            <DailyBriefingChatPanel
              key={`agent-chat-${chatSessionKey}-${workflow.briefing?.source_snapshot_hash ?? "no-briefing"}`}
              companyId={workflow.companyId}
              date={workflow.date}
              onOpenDocumentDraft={(action) => void workflow.openDocumentDraft(action)}
              onOpenHandoffPreview={(action) => void workflow.openHandoffPreview(action)}
              onOpenCitation={(citationId) => void workflow.openCitation(citationId)}
              selectedActionId={documentAction?.action_id ?? handoffAction?.action_id ?? null}
              selectedCaseId={documentAction?.case_id ?? handoffAction?.case_id ?? null}
            />
          </aside>
        </div>
      ) : null}
    </div>
  );
}

function WorkerRegisterDrawer({ companyId, onClose }: { companyId: string; onClose: () => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [temporaryPassword, setTemporaryPassword] = useState("worker1234");
  const [nationality, setNationality] = useState("베트남");
  const [preferredLanguage, setPreferredLanguage] = useState("vi");
  const [visaType, setVisaType] = useState("E-9");
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);

  async function submit() {
    setWorking(true);
    setMessage("");
    try {
      const response = await fetch("/api/v1/workers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          temporary_password: temporaryPassword,
          company_id: companyId,
          nationality,
          preferred_language: preferredLanguage,
          visa_type: visaType,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setMessage(data.detail || "근로자 등록에 실패했습니다.");
        return;
      }
      const data = await response.json();
      setMessage(
        `${data.worker?.name ?? name} 등록과 근로자 계정 생성이 완료됐습니다. 임시 비밀번호로 최초 로그인 후 비밀번호를 변경해야 합니다.`,
      );
    } finally {
      setWorking(false);
    }
  }

  return (
    <PcDrawer title="근로자 등록" onClose={onClose}>
      <div className={styles.modalStack}>
        <label className={styles.formLabel}>
          근로자 이름
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Nguyen Van B" />
        </label>
        <label className={styles.formLabel}>
          로그인 이메일
          <input value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className={styles.formLabel}>
          국적
          <input value={nationality} onChange={(event) => setNationality(event.target.value)} />
        </label>
        <label className={styles.formLabel}>
          언어
          <select value={preferredLanguage} onChange={(event) => setPreferredLanguage(event.target.value)}>
            <option value="vi">Tiếng Việt</option>
            <option value="id">Bahasa Indonesia</option>
            <option value="ko">한국어</option>
          </select>
        </label>
        <label className={styles.formLabel}>
          체류자격
          <input value={visaType} onChange={(event) => setVisaType(event.target.value)} />
        </label>
        <label className={styles.formLabel}>
          임시 비밀번호
          <input value={temporaryPassword} onChange={(event) => setTemporaryPassword(event.target.value)} />
        </label>
        {message ? <p className={styles.safeNotice}>{message}</p> : null}
        <button className={styles.primaryWideButton} disabled={working || !name || !email} onClick={submit} type="button">
          근로자 등록
        </button>
      </div>
    </PcDrawer>
  );
}

function findAction(actions: NextAction[], actionType: NextAction["action_type"]) {
  return (
    actions.find((action) => action.action_type === actionType && action.status === "pending_approval") ??
    actions.find((action) => action.action_type === actionType) ??
    null
  );
}

function AgentSummaryBox({ result }: { result: AgentReviewResult }) {
  const s = result.summary_structured;
  const rows: Array<{ label: string; value: React.ReactNode }> = [];

  if (s.visa_risk) rows.push({ label: "비자 위험도", value: s.visa_risk });
  if (s.doc_priority) rows.push({ label: "서류 우선순위", value: s.doc_priority });
  if (s.missing_critical && s.missing_critical.length > 0) {
    rows.push({
      label: "필수 서류 누락",
      value: (
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          {s.missing_critical.map((doc) => <li key={doc}>{doc}</li>)}
        </ul>
      ),
    });
  }
  if (s.missing_supplementary && s.missing_supplementary.length > 0) {
    rows.push({
      label: "보완 서류",
      value: (
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          {s.missing_supplementary.map((doc) => <li key={doc}>{docCodeToKo(doc)}</li>)}
        </ul>
      ),
    });
  }

  if (rows.length === 0) {
    return (
      <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#166534" }}>
        위험 항목 없음 — 현재 상태 양호
      </div>
    );
  }

  return (
    <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, overflow: "hidden" }}>
      {rows.map((row, idx) => (
        <div key={row.label} style={{ display: "grid", gridTemplateColumns: "130px minmax(0,1fr)", gap: 10, padding: "9px 14px", borderBottom: idx < rows.length - 1 ? "1px solid #EEF2F7" : "none", fontSize: 13 }}>
          <span style={{ color: "#64748B", fontWeight: 500 }}>{row.label}</span>
          <span style={{ fontWeight: 600, color: "#1E293B" }}>{row.value}</span>
        </div>
      ))}
    </div>
  );
}

function ReviewActionBar({
  action,
  workflow,
  documentAction,
  onDocumentDraftOpen,
  onClose,
}: {
  action: NextAction | null;
  workflow: ReturnType<typeof useDailyBriefingWorkflow>;
  documentAction: NextAction | null;
  onDocumentDraftOpen: () => void;
  onClose: () => void;
}) {
  const router = useRouter();
  const [working, setWorking] = useState(false);
  const [localStatus, setLocalStatus] = useState<string | null>(null);
  const [threads, setThreads] = useState<ActionContactThread[]>([]);
  const [revisionMode, setRevisionMode] = useState(false);
  const [revisionReason, setRevisionReason] = useState("");

  const status = localStatus ?? action?.status ?? null;

  async function handleApprove() {
    if (!action) return;
    setWorking(true);
    try {
      const result = await workflow.approve(action);
      if (result) {
        setLocalStatus("approved");
        const created = await getActionContactThreads(action.action_id, workflow.companyId);
        setThreads(created);
      }
    } finally {
      setWorking(false);
    }
  }

  async function handleReject() {
    if (!action) return;
    setWorking(true);
    try {
      const result = await workflow.reject(action);
      if (result) setLocalStatus("rejected");
    } finally {
      setWorking(false);
    }
  }

  async function handleRevision() {
    if (!action || !revisionReason.trim()) return;
    setWorking(true);
    try {
      const result = await workflow.requestActionRevision(action, revisionReason);
      if (result) { setLocalStatus("revision_requested"); setRevisionMode(false); }
    } finally {
      setWorking(false);
    }
  }

  function navigateToMessages(threadId?: string, isExpert?: boolean) {
    onClose();
    const params = new URLSearchParams();
    if (threadId) params.set("thread_id", threadId);
    if (isExpert) params.set("tab", "expert");
    router.push(`/contacts?${params.toString()}`);
  }

  const btnBase: React.CSSProperties = { border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: working ? "not-allowed" : "pointer", opacity: working ? 0.6 : 1 };

  if (!action) {
    return <p style={{ fontSize: 13, color: "#94A3B8" }}>연결된 액션이 없습니다.</p>;
  }

  if (status === "rejected") {
    return (
      <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#991B1B", fontWeight: 600 }}>
        거절됨
      </div>
    );
  }

  if (status === "revision_requested") {
    return (
      <div style={{ background: "#FFFBEB", border: "1px solid #FDE68A", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#92400E", fontWeight: 600 }}>
        수정 요청됨
      </div>
    );
  }

  if (status === "approved") {
    return (
      <div className={styles.modalStack}>
        <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#166534", fontWeight: 600 }}>
          승인됨 ✓
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {threads.length > 0 ? (
            threads.map((thread) => (
              <button
                key={thread.id}
                type="button"
                onClick={() => navigateToMessages(thread.id, thread.title.includes("행정사"))}
                style={{ ...btnBase, background: "#1D4ED8", color: "#fff", cursor: "pointer", opacity: 1 }}
              >
                {thread.title.includes("행정사") ? "행정사 메시지 보기" : "메시지관리에서 보기"}
              </button>
            ))
          ) : (
            <button type="button" onClick={() => navigateToMessages()} style={{ ...btnBase, background: "#1D4ED8", color: "#fff", cursor: "pointer", opacity: 1 }}>
              메시지관리에서 보기
            </button>
          )}
          {documentAction ? (
            <button type="button" onClick={onDocumentDraftOpen} style={{ ...btnBase, background: "#F1F5F9", color: "#1E293B", cursor: "pointer", opacity: 1 }}>
              서류 요청 초안 보기
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.modalStack}>
      {revisionMode ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <textarea
            value={revisionReason}
            onChange={(e) => setRevisionReason(e.target.value)}
            placeholder="수정 요청 사유를 입력하세요"
            rows={3}
            style={{ fontSize: 13, padding: "8px 10px", borderRadius: 6, border: "1px solid #CBD5E1", resize: "vertical" }}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" disabled={working || !revisionReason.trim()} onClick={handleRevision} style={{ ...btnBase, background: "#F59E0B", color: "#fff" }}>
              {working ? "처리 중…" : "수정 요청 전송"}
            </button>
            <button type="button" onClick={() => setRevisionMode(false)} style={{ ...btnBase, background: "#F1F5F9", color: "#64748B" }}>
              취소
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" disabled={working} onClick={handleApprove} style={{ ...btnBase, background: "#16A34A", color: "#fff" }}>
            {working ? "처리 중…" : "승인"}
          </button>
          <button type="button" disabled={working} onClick={() => setRevisionMode(true)} style={{ ...btnBase, background: "#F59E0B", color: "#fff" }}>
            수정 요청
          </button>
          <button type="button" disabled={working} onClick={handleReject} style={{ ...btnBase, background: "#EF4444", color: "#fff" }}>
            거절
          </button>
        </div>
      )}
    </div>
  );
}

function HandoffReadablePreview({
  action,
  briefingItem,
  companyId,
  workflow,
  documentAction,
  onClose,
}: {
  action: NextAction | null;
  briefingItem: DailyBriefingItem | null;
  companyId: string;
  workflow: ReturnType<typeof useDailyBriefingWorkflow>;
  documentAction: NextAction | null;
  onClose: () => void;
}) {
  const [agentResult, setAgentResult] = useState<AgentReviewResult | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentError, setAgentError] = useState<string | null>(null);

  const rowStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "150px minmax(0, 1fr)",
    gap: 12,
    padding: "9px 0",
    borderBottom: "1px solid #EEF2F7",
  };

  async function handleRunAgentReview() {
    if (!action) return;
    setAgentLoading(true);
    setAgentError(null);
    try {
      const result = await runAgentReview(action.action_id, companyId);
      setAgentResult(result);
    } catch (err) {
      setAgentError(err instanceof Error ? err.message : "분석 실패");
    } finally {
      setAgentLoading(false);
    }
  }

  async function handleDocumentDraftOpen() {
    if (!documentAction) return;
    onClose();
    await workflow.openDocumentDraft(documentAction);
  }

  const riskType = briefingItem?.risk_type ?? "visa_expiry";
  const title = RISK_TYPE_TITLE[riskType] ?? "검토 요청서";
  const subjectName = briefingItem?.subject_display_name ?? briefingItem?.subject_display_id ?? "—";
  const missingDocs = briefingItem?.missing_documents ?? [];
  const submittedDocs = missingDocs.length === 0 ? "서류 보완 없음" : `${missingDocs.map(docCodeToKo).join(", ")} 미제출`;

  return (
    <div className={styles.modalStack}>
      <p className={styles.safeNotice}>
        행정사에게 전달하기 전 담당자가 확인할 검토 문서입니다. 개인정보는 필요한 범위만 포함하고, 정부 포털 제출이나 외부 전달은 자동 수행하지 않습니다.
      </p>

      {action ? (
        <div>
          {agentResult ? (
            <AgentSummaryBox result={agentResult} />
          ) : agentError ? (
            <p style={{ color: "#EF4444", fontSize: 12 }}>{agentError}</p>
          ) : null}
          {!agentResult && (
            <button
              type="button"
              disabled={agentLoading}
              onClick={handleRunAgentReview}
              style={{ border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: agentLoading ? "not-allowed" : "pointer", opacity: agentLoading ? 0.6 : 1, background: "#F1F5F9", color: "#1E293B" }}
            >
              {agentLoading ? "에이전트 분석 중…" : "에이전트 분석 실행"}
            </button>
          )}
        </div>
      ) : null}

      <section>
        <h3>{title}</h3>
        <div style={rowStyle}><span className={styles.subtle}>수신</span><strong>담당 행정사</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>요청 목적</span><strong>체류기간 연장 가능 일정과 준비 서류 검토</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>대상 근로자</span><strong>{subjectName}</strong></div>
        {briefingItem?.severity ? (
          <div style={rowStyle}><span className={styles.subtle}>현재 상태</span><strong>{briefingItem.severity}</strong></div>
        ) : null}
        {missingDocs.length > 0 ? (
          <div style={rowStyle}><span className={styles.subtle}>누락 서류</span><strong>{missingDocs.map(docCodeToKo).join(", ")}</strong></div>
        ) : null}
      </section>
      <section>
        <h3>요청 내용</h3>
        <p style={{ lineHeight: 1.8, margin: 0 }}>
          아래 근로자의 체류기간 연장 준비와 관련하여 현재 일정, 제출 서류, 추가 보완 필요 항목을 검토해 주세요.
          검토 결과는 담당자가 내부 승인 후 후속 안내에 사용할 예정이며, 본 요청만으로 정부 포털 제출이나 대외 발송은 진행하지 않습니다.
        </p>
      </section>
      <section>
        <h3>첨부 및 참고 근거</h3>
        <div style={rowStyle}><span className={styles.subtle}>제출 서류</span><strong>{submittedDocs}</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>공식 근거</span><strong>출입국관리법 제25조, HiKorea 체류기간 연장허가 신청 안내</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>처리 원칙</span><strong>행정사 검토 후 담당자 승인 전까지 외부 제출 없음</strong></div>
      </section>

      <section>
        <h3>담당자 검토 액션</h3>
        <ReviewActionBar
          action={action}
          workflow={workflow}
          documentAction={documentAction}
          onDocumentDraftOpen={handleDocumentDraftOpen}
          onClose={onClose}
        />
      </section>
    </div>
  );
}

function PcDrawer({
  children,
  title,
  onClose,
}: {
  children: React.ReactNode;
  title: string;
  onClose: () => void;
}) {
  return (
    <div className={styles.drawerOverlay}>
      <button className={styles.drawerBackdrop} aria-label={`${title} 닫기`} onClick={onClose} type="button" />
      <aside className={styles.drawer}>
        <div className={styles.drawerHeader}>
          <h2>{title}</h2>
          <button className={styles.closeButton} onClick={onClose} type="button">
            닫기
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}
