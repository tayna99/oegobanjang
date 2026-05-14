"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BriefcaseBusiness,
  CalendarCheck,
  Clock3,
  FileCheck2,
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
  AdminReviewView,
  CasesView,
  ContactView,
  HiringPreparationView,
  JudgmentLogView,
  TodayTasksView,
  WorkersView,
  type PcViewAction,
} from "./views";
import type { DailyBriefingResult, NextAction } from "../../types/dailyBriefing";
import { DailyBriefingChatPanel } from "../dashboard/DailyBriefingChatPanel";
import { useDailyBriefingWorkflow } from "../dashboard/useDailyBriefingWorkflow";
import { clearOperatorContext, getOperatorContext, type OperatorContext } from "../../lib/operatorContext";

const routes: Array<{ key: PcViewKey; href: string; label: string; icon: React.ElementType }> = [
  { key: "today", href: "/dashboard", label: "오늘 할 일", icon: CalendarCheck },
  { key: "hiring", href: "/hiring", label: "채용 준비", icon: UserRoundPlus },
  { key: "workers", href: "/workers", label: "근로자", icon: Users },
  { key: "contact", href: "/contacts", label: "메시지 관리", icon: MessageSquare },
  { key: "admin", href: "/documents", label: "행정사 검토", icon: FileCheck2 },
  { key: "judgment", href: "/evidence", label: "판단 기록", icon: Clock3 },
];

const pathToView: Record<string, PcViewKey> = {
  "/dashboard": "today",
  "/hiring": "hiring",
  "/workers": "workers",
  "/contacts": "contact",
  "/visa": "cases",
  "/documents": "admin",
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
) {
  if (view === "hiring") return <HiringPreparationView onAction={onAction} />;
  if (view === "workers") return <WorkersView onAction={onAction} />;
  if (view === "contact") return <ContactView onAction={onAction} />;
  if (view === "cases") return <CasesView onAction={onAction} />;
  if (view === "admin") return <AdminReviewView onAction={onAction} />;
  if (view === "judgment") return <JudgmentLogView onAction={onAction} />;
  return <TodayTasksView briefing={briefing} loading={loading} onAction={onAction} />;
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

  useEffect(() => {
    if (operator?.accessToken) {
      void workflow.runBriefing();
    }
  }, [operator?.accessToken, workflow.runBriefing]);

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
    if (action) {
      await workflow.openHandoffPreview(action);
      return;
    }
    setPanel({
      title: "검토 자료 미리보기",
      body: <HandoffReadablePreview />,
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
      await openHandoffPreview(null);
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
    if (query.includes("메시지") || lower.includes("message") || lower.includes("nguyen")) {
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
              aria-label="근로자, 서류, 메시지 검색"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="근로자, 서류, 메시지 검색"
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
        {children ?? renderView(activeView, (action) => void handleAction(action), workflow.briefing, workflow.loading)}
      </main>

      <button className={styles.fab} data-testid="ai-fab" onClick={() => setChatOpen(true)} type="button">
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
          <div className={styles.modalStack}>
            <pre className={styles.previewBox}>
              {typeof workflow.preview.content_redacted === "string"
                ? workflow.preview.content_redacted
                : JSON.stringify(workflow.preview.content_redacted, null, 2)}
            </pre>
            <p className={styles.safeNotice}>검토용 초안입니다. 외부 전달은 수행하지 않았습니다.</p>
          </div>
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
        <p className={styles.safeNotice}>등록과 동시에 근로자 로그인 계정이 생성됩니다. 비밀번호는 DB에 원문이 아닌 PBKDF2 해시로 저장됩니다.</p>
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

function HandoffReadablePreview() {
  const rowStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "150px minmax(0, 1fr)",
    gap: 12,
    padding: "9px 0",
    borderBottom: "1px solid #EEF2F7",
  };
  return (
    <div className={styles.modalStack}>
      <p className={styles.safeNotice}>
        행정사에게 전달하기 전 담당자가 확인할 검토 문서입니다. 개인정보는 필요한 범위만 포함하고, 정부 포털 제출이나 외부 전달은 자동 수행하지 않습니다.
      </p>
      <section>
        <h3>체류기간 연장 검토 요청서</h3>
        <div style={rowStyle}><span className={styles.subtle}>수신</span><strong>담당 행정사</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>요청 목적</span><strong>E-9 근로자 체류기간 연장 가능 일정과 준비 서류 검토</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>대상 근로자</span><strong>Nguyen V. / 베트남 / E-9</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>사업장</span><strong>삼성전자 부산공장 · 부산공장 조립라인</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>현재 상태</span><strong>체류만료일 및 제출 서류 확인 필요, 여권 사본은 근로자 제출 완료</strong></div>
      </section>
      <section>
        <h3>요청 내용</h3>
        <p style={{ lineHeight: 1.8, margin: 0 }}>
          아래 근로자의 체류기간 연장 준비와 관련하여 현재 일정, 제출 서류, 추가 보완 필요 항목을 검토해 주세요.
          검토 결과는 담당자가 내부 승인 후 후속 안내에 사용할 예정이며, 본 요청만으로 정부 포털 제출이나 대외 발송은 진행하지 않습니다.
        </p>
      </section>
      <section>
        <h3>검토 요청 항목</h3>
        <ol style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
          <li>체류기간 연장 신청 가능 일정과 준비 마감일 확인</li>
          <li>여권 사본 제출본의 식별 가능 여부와 보완 필요 여부 확인</li>
          <li>외국인등록증 사본, 표준근로계약서 등 추가 제출 필요 서류 확인</li>
          <li>회사 담당자가 준비해야 할 사업장 또는 고용 관련 확인 자료 목록 회신</li>
        </ol>
      </section>
      <section>
        <h3>첨부 및 참고 근거</h3>
        <div style={rowStyle}><span className={styles.subtle}>제출 서류</span><strong>여권 사본 제출됨</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>공식 근거</span><strong>출입국관리법 제25조, HiKorea 체류기간 연장허가 신청 안내</strong></div>
        <div style={rowStyle}><span className={styles.subtle}>처리 원칙</span><strong>행정사 검토 후 담당자 승인 전까지 외부 제출 없음</strong></div>
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
