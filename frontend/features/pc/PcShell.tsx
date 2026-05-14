"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  BriefcaseBusiness,
  CalendarCheck,
  ClipboardList,
  Clock3,
  FileCheck2,
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
import type { NextAction } from "../../types/dailyBriefing";
import { DailyBriefingChatPanel } from "../dashboard/DailyBriefingChatPanel";
import { useDailyBriefingWorkflow } from "../dashboard/useDailyBriefingWorkflow";

const routes: Array<{ key: PcViewKey; href: string; label: string; icon: React.ElementType }> = [
  { key: "today", href: "/dashboard", label: "오늘 할 일", icon: CalendarCheck },
  { key: "hiring", href: "/hiring", label: "채용 준비", icon: UserRoundPlus },
  { key: "workers", href: "/workers", label: "근로자", icon: Users },
  { key: "contact", href: "/contacts", label: "컨택", icon: MessageSquare },
  { key: "cases", href: "/visa", label: "케이스", icon: ClipboardList },
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

function renderView(view: PcViewKey, onAction: (action: PcViewAction) => void) {
  if (view === "hiring") return <HiringPreparationView onAction={onAction} />;
  if (view === "workers") return <WorkersView onAction={onAction} />;
  if (view === "contact") return <ContactView onAction={onAction} />;
  if (view === "cases") return <CasesView onAction={onAction} />;
  if (view === "admin") return <AdminReviewView onAction={onAction} />;
  if (view === "judgment") return <JudgmentLogView onAction={onAction} />;
  return <TodayTasksView onAction={onAction} />;
}

type InfoPanel = {
  title: string;
  body: React.ReactNode;
};

export function PcShell() {
  const pathname = usePathname();
  const activeView = pathToView[pathname] ?? "today";
  const workflow = useDailyBriefingWorkflow();
  const [chatOpen, setChatOpen] = useState(false);
  const [panel, setPanel] = useState<InfoPanel | null>(null);

  useEffect(() => {
    void workflow.runBriefing();
  }, [workflow.runBriefing]);

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
      body: (
        <div className={styles.modalStack}>
          <p>행정사 검토용 초안입니다. 승인 후에도 정부 포털 제출은 자동 수행하지 않습니다.</p>
          <ul>
            <li>근로자: Nguyen V. / Dang T.</li>
            <li>검토 항목: 체류기간, 누락 서류, 이전 요청 이력</li>
            <li>상태: 담당자 검토 대기</li>
          </ul>
        </div>
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
      await openHandoffPreview(handoffAction);
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
      setPanel({
        title: "근로자 등록",
        body: <p>근로자 등록 폼은 후속 구현 영역입니다. 현재 화면에서는 기존 근로자 상태 확인만 제공합니다.</p>,
      });
      return;
    }
    setPanel({
      title: action.label,
      body: <p>응답 요약과 이전 대화 기록을 확인하는 검토용 화면입니다.</p>,
    });
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

          <div className={styles.search} aria-label="검색">
            <Search size={16} />
            <span>근로자, 케이스, 서류, 메시지 검색</span>
          </div>

          <div className={styles.rightCluster}>
            <button className={styles.iconButton} type="button" aria-label="알림">
              <Bell size={20} />
              <span className={styles.noticeCount}>12</span>
            </button>
            <div className={styles.person}>
              <span className={styles.avatar}>김</span>
              <span>
                <span className={styles.manager}>{company.manager}</span>
                <span className={styles.role}>{company.role}</span>
              </span>
            </div>
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

      <main className={styles.main}>{renderView(activeView, (action) => void handleAction(action))}</main>

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

function findAction(actions: NextAction[], actionType: NextAction["action_type"]) {
  return (
    actions.find((action) => action.action_type === actionType && action.status === "pending_approval") ??
    actions.find((action) => action.action_type === actionType) ??
    null
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
