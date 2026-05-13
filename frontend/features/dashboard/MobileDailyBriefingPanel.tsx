"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import type { AgentChatResponse, DailyBriefingItem, NextAction } from "../../types/dailyBriefing";
import { useAgentChat } from "./useAgentChat";
import { useDailyBriefingWorkflow } from "./useDailyBriefingWorkflow";

const riskTypeLabel: Record<DailyBriefingItem["risk_type"], string> = {
  candidate_readiness: "입국 예정자 서류",
  contract_visa_conflict: "계약-체류 충돌",
  missing_document: "누락 서류",
  quota_review: "신규 고용 준비",
  reporting_deadline: "신고기한",
  visa_expiry: "체류만료",
};

const severityColor = {
  CRITICAL: "#B42318",
  HIGH: "#B45309",
  MEDIUM: "#9A6700",
  LOW: "#2563EB",
};

const bottomTabs = [
  { id: "home", label: "홈" },
  { id: "workers", label: "근로자" },
  { id: "contact", label: "컨택" },
  { id: "cases", label: "케이스" },
  { id: "more", label: "더보기" },
] as const;

const mobilePrompts = [
  "오늘 먼저 봐야 할 외국인 업무 뭐야?",
  "비자 끝난 사람 있나?",
  "여권 사본 안 받은 사람만 알려줘",
  "사람 더 필요하면 뭐부터 보면 돼?",
];

function formatMobileDate(date: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date(`${date}T00:00:00+09:00`));
}

function timingLabel(item: DailyBriefingItem) {
  if (item.risk_timing_label) {
    return item.risk_timing_label;
  }
  if (item.expired) {
    return `D+${item.days_overdue ?? 0}`;
  }
  if (item.d_day !== null) {
    return `D-${item.d_day}`;
  }
  return "기한 확인 필요";
}

export function MobileDailyBriefingPanel() {
  const workflow = useDailyBriefingWorkflow();
  const [activeBottomTab, setActiveBottomTab] = useState<(typeof bottomTabs)[number]["id"]>("home");

  const {
    briefing,
    citationChunk,
    citationSource,
    citationValidation,
    companyId,
    date,
    documentDraft,
    error,
    loading,
    openCitation,
    openDocumentDraft,
    openHandoffPreview,
    preview,
    runBriefing,
    setCitationChunk,
    setCitationSource,
    setCitationValidation,
    setDocumentDraft,
    setPreview,
  } = workflow;

  const chat = useAgentChat({
    companyId,
    date,
    workspaceId: "next_mobile_daily_briefing",
    activeTab: "mobile_daily_briefing",
  });

  useEffect(() => {
    void runBriefing();
    // The mobile briefing should load once on entry; date changes happen on the PC operations panel.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pendingActions = useMemo(
    () => briefing?.recommended_actions.filter((action) => action.status === "pending_approval") ?? [],
    [briefing],
  );
  const topItems = briefing?.items.slice(0, 5) ?? [];

  function handleChatAction(action: NextAction) {
    if (action.action_type === "request_document") {
      void openDocumentDraft(action);
      return;
    }
    void openHandoffPreview(action);
  }

  function handleChatSource(response: AgentChatResponse) {
    const citationId = response.sources[0]?.citation_id;
    if (citationId) {
      void openCitation(citationId);
    }
  }

  return (
    <section
      style={{
        display: "grid",
        justifyContent: "center",
        padding: "12px 0 28px",
      }}
    >
      <div
        style={{
          background: "#F8FAFC",
          border: "1px solid rgba(15,23,42,0.12)",
          borderRadius: 28,
          boxShadow: "0 24px 70px rgba(15,23,42,0.18)",
          display: "flex",
          flexDirection: "column",
          height: "min(860px, calc(100vh - 100px))",
          minHeight: 720,
          overflow: "hidden",
          width: "min(430px, calc(100vw - 32px))",
        }}
      >
        <header
          style={{
            background: "#fff",
            borderBottom: "1px solid rgba(15,23,42,0.09)",
            padding: "24px 16px 14px",
          }}
        >
          <div style={{ alignItems: "center", display: "flex", gap: 10 }}>
            <div
              style={{
                alignItems: "center",
                background: "linear-gradient(135deg, #1B3FA0, #00BFA5)",
                borderRadius: 9,
                color: "#fff",
                display: "flex",
                fontSize: 14,
                fontWeight: 900,
                height: 30,
                justifyContent: "center",
                width: 30,
              }}
            >
              반
            </div>
            <strong style={{ color: "#1B3FA0", fontSize: 18 }}>외고반장</strong>
            <span style={{ flex: 1 }} />
            <span
              style={{
                background: pendingActions.length ? "#EF4444" : "#E2E8F0",
                borderRadius: 999,
                color: pendingActions.length ? "#fff" : "#475569",
                fontSize: 11,
                fontWeight: 900,
                padding: "4px 8px",
              }}
            >
              {pendingActions.length}건
            </span>
          </div>
          <div style={{ alignItems: "flex-end", display: "flex", gap: 12, marginTop: 18 }}>
            <div>
              <h1 style={{ color: "#0F172A", fontSize: 22, margin: 0 }}>오늘 브리핑</h1>
              <p style={{ color: "#64748B", fontSize: 12, margin: "4px 0 0" }}>
                {formatMobileDate(date)}
              </p>
            </div>
            <span style={{ flex: 1 }} />
            <span
              style={{
                background: "#EFF6FF",
                border: "1px solid #BFDBFE",
                borderRadius: 999,
                color: "#1D4ED8",
                fontSize: 12,
                fontWeight: 800,
                padding: "7px 11px",
              }}
            >
              한별제조
            </span>
          </div>
        </header>

        <main style={{ display: "flex", flex: 1, flexDirection: "column", minHeight: 0 }}>
          {activeBottomTab === "home" ? (
            <>
              <div
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: "14px 14px 12px",
                }}
              >
                <div
                  style={{
                    background: "linear-gradient(110deg, rgba(27,63,160,0.07), rgba(0,191,165,0.06))",
                    border: "1px solid rgba(27,63,160,0.15)",
                    borderRadius: 14,
                    padding: "12px 14px",
                  }}
                >
                  <div style={{ alignItems: "center", display: "flex", gap: 7 }}>
                    <span
                      style={{
                        background: "linear-gradient(135deg, #1B3FA0, #00BFA5)",
                        borderRadius: 7,
                        color: "#fff",
                        fontSize: 11,
                        fontWeight: 900,
                        padding: "5px 7px",
                      }}
                    >
                      반
                    </span>
                    <strong style={{ color: "#1B3FA0", fontSize: 12 }}>AI 반장</strong>
                    <span style={{ color: "#94A3B8", fontSize: 11 }}>실시간 API</span>
                  </div>
                  <p style={{ color: "#0F172A", fontSize: 13.5, lineHeight: 1.6, margin: "9px 0 0" }}>
                    대표님, 오늘 확인이 필요한 외국인 고용 업무가{" "}
                    <strong style={{ color: "#1B3FA0" }}>
                      {briefing?.risk_summary.total_count ?? 0}건
                    </strong>
                    입니다. 급한 케이스와 승인 필요한 초안만 먼저 보여드립니다.
                  </p>
                </div>

                {loading ? (
                  <div style={emptyStateStyle}>브리핑을 불러오는 중...</div>
                ) : null}
                {error ? <div style={errorStateStyle}>API 연결 실패: {error}</div> : null}

                <div
                  style={{
                    alignItems: "center",
                    display: "flex",
                    gap: 8,
                    margin: "18px 2px 9px",
                  }}
                >
                  <strong style={{ color: "#0F172A", fontSize: 13 }}>승인 대기 업무</strong>
                  <span
                    style={{
                      background: "rgba(245,158,11,0.14)",
                      border: "1px solid rgba(245,158,11,0.35)",
                      borderRadius: 999,
                      color: "#9C5800",
                      fontSize: 11,
                      fontWeight: 800,
                      padding: "2px 8px",
                    }}
                  >
                    {pendingActions.length}건
                  </span>
                </div>

                <div style={{ display: "grid", gap: 12 }}>
                  {topItems.map((item) => (
                    <MobileRiskCard
                      item={item}
                      key={item.item_id}
                      onOpenCitation={openCitation}
                      onOpenDocumentDraft={openDocumentDraft}
                      onOpenHandoffPreview={openHandoffPreview}
                      recommendedActions={briefing?.recommended_actions ?? []}
                    />
                  ))}
                  {!loading && topItems.length === 0 ? (
                    <div style={emptyStateStyle}>오늘 확인할 업무가 없습니다.</div>
                  ) : null}
                </div>

                <MobileChatThread
                  messages={chat.messages}
                  onAction={handleChatAction}
                  onShowSource={handleChatSource}
                  prompts={mobilePrompts}
                  sendMessage={chat.sendMessage}
                />

                {documentDraft ? (
                  <MobileSheet title="서류 요청 초안" onClose={() => setDocumentDraft(null)}>
                    <p style={sheetTextStyle}>{documentDraft.korean_text}</p>
                    <p style={sheetTextStyle}>{documentDraft.translated_text}</p>
                    <p style={sheetNoticeStyle}>승인 전에는 외부로 발송되지 않습니다.</p>
                  </MobileSheet>
                ) : null}

                {preview ? (
                  <MobileSheet title="행정사 검토 패키지" onClose={() => setPreview(null)}>
                    <pre style={sheetPreStyle}>{JSON.stringify(preview.content_redacted, null, 2)}</pre>
                    <p style={sheetNoticeStyle}>검토용 초안입니다. 외부 전달은 수행하지 않았습니다.</p>
                  </MobileSheet>
                ) : null}

                {citationChunk && citationSource && citationValidation ? (
                  <MobileSheet
                    title="판단 근거"
                    onClose={() => {
                      setCitationChunk(null);
                      setCitationSource(null);
                      setCitationValidation(null);
                    }}
                  >
                    <p style={sheetTextStyle}>{citationSource.title}</p>
                    <p style={sheetTextStyle}>{citationChunk.chunk_text}</p>
                    <p style={sheetNoticeStyle}>검증 상태: {citationValidation.validation_status}</p>
                  </MobileSheet>
                ) : null}
              </div>

              <form
                onSubmit={chat.handleSubmit}
                style={{
                  background: "rgba(248,250,252,0.96)",
                  borderTop: "1px solid rgba(15,23,42,0.09)",
                  padding: "8px 12px 10px",
                }}
              >
                <div
                  style={{
                    alignItems: "center",
                    background: "#fff",
                    border: "1.5px solid #1B3FA0",
                    borderRadius: 14,
                    boxShadow: "0 2px 8px rgba(27,63,160,0.08)",
                    display: "flex",
                    gap: 8,
                    padding: "5px 6px 5px 12px",
                  }}
                >
                  <input
                    disabled={chat.loading}
                    onChange={(event) => chat.setDraft(event.target.value)}
                    placeholder="외국인 고용 업무 관련 질문..."
                    style={{
                      background: "transparent",
                      border: 0,
                      color: "#0F172A",
                      flex: 1,
                      font: "inherit",
                      fontSize: 13.5,
                      minWidth: 0,
                      outline: "none",
                      padding: "9px 0",
                    }}
                    value={chat.draft}
                  />
                  <button
                    disabled={chat.loading || !chat.draft.trim()}
                    style={{
                      background:
                        chat.draft.trim() && !chat.loading
                          ? "linear-gradient(135deg, #1B3FA0, #00BFA5)"
                          : "#CBD5E1",
                      border: 0,
                      borderRadius: 999,
                      color: "#fff",
                      cursor: chat.loading || !chat.draft.trim() ? "default" : "pointer",
                      fontSize: 11.5,
                      fontWeight: 900,
                      height: 34,
                      width: chat.loading ? 64 : 34,
                    }}
                    type="submit"
                  >
                    {chat.loading ? "확인 중" : "→"}
                  </button>
                </div>
                {chat.error ? <p style={{ ...errorStateStyle, margin: "8px 0 0" }}>{chat.error}</p> : null}
              </form>
            </>
          ) : (
            <div style={emptyStateStyle}>이 탭은 PC 운영 화면에서 확인할 수 있습니다.</div>
          )}
        </main>

        <nav
          aria-label="모바일 하단 탭"
          style={{
            background: "rgba(255,255,255,0.96)",
            borderTop: "1px solid rgba(15,23,42,0.09)",
            display: "flex",
            padding: "7px 0 6px",
          }}
        >
          {bottomTabs.map((tab) => {
            const active = activeBottomTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveBottomTab(tab.id)}
                style={{
                  background: "transparent",
                  border: 0,
                  color: active ? "#1B3FA0" : "#94A3B8",
                  cursor: "pointer",
                  flex: 1,
                  font: "inherit",
                  fontSize: 11,
                  fontWeight: active ? 900 : 700,
                  padding: "8px 0",
                }}
                type="button"
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>
    </section>
  );
}

function MobileRiskCard({
  item,
  recommendedActions,
  onOpenDocumentDraft,
  onOpenHandoffPreview,
  onOpenCitation,
}: {
  item: DailyBriefingItem;
  recommendedActions: NextAction[];
  onOpenDocumentDraft: (action: NextAction) => void;
  onOpenHandoffPreview: (action: NextAction) => void;
  onOpenCitation: (citationId: string) => void;
}) {
  const actions = recommendedActions.filter((action) => item.next_action_ids.includes(action.action_id));
  const tone = severityColor[item.severity];

  return (
    <article
      style={{
        background: "#fff",
        border: "1px solid rgba(15,23,42,0.09)",
        borderRadius: 16,
        borderTop: `3px solid ${tone}`,
        boxShadow: "0 1px 6px rgba(15,23,42,0.06)",
        overflow: "hidden",
      }}
    >
      <div style={{ padding: "14px 16px" }}>
        <div style={{ alignItems: "center", display: "flex", gap: 6, marginBottom: 8 }}>
          <span
            style={{
              background: `${tone}14`,
              borderRadius: 999,
              color: tone,
              fontSize: 11.5,
              fontWeight: 900,
              padding: "3px 9px",
            }}
          >
            {item.severity}
          </span>
          <span style={{ color: "#475569", fontSize: 12, fontWeight: 800 }}>
            {riskTypeLabel[item.risk_type]}
          </span>
          <span style={{ color: tone, fontSize: 12.5, fontWeight: 900, marginLeft: "auto" }}>
            {timingLabel(item)}
          </span>
        </div>
        <h2 style={{ color: "#0F172A", fontSize: 15.5, lineHeight: 1.35, margin: 0 }}>
          {item.case_title ?? item.subject_display_name ?? item.subject_display_id ?? item.subject_id}
        </h2>
        {item.case_summary ? (
          <p style={{ color: "#475569", fontSize: 13, lineHeight: 1.55, margin: "6px 0 0" }}>
            {item.case_summary}
          </p>
        ) : null}
        {item.missing_documents.length ? (
          <p style={{ color: tone, fontSize: 12.5, fontWeight: 800, margin: "8px 0 0" }}>
            누락 서류: {item.missing_documents.join(", ")}
          </p>
        ) : null}
      </div>
      <div style={{ display: "flex", gap: 8, padding: "0 16px 14px" }}>
        {actions.map((action) => (
          <button
            key={action.action_id}
            onClick={() =>
              action.action_type === "request_document"
                ? onOpenDocumentDraft(action)
                : onOpenHandoffPreview(action)
            }
            style={cardButtonStyle}
            type="button"
          >
            {action.action_type === "request_document" ? "초안 보기" : "패키지 보기"}
          </button>
        ))}
        {item.citation_ids[0] ? (
          <button
            onClick={() => onOpenCitation(item.citation_ids[0])}
            style={{ ...cardButtonStyle, background: "#fff", color: "#1B3FA0" }}
            type="button"
          >
            근거
          </button>
        ) : null}
      </div>
      <div style={{ color: "#94A3B8", fontSize: 11, padding: "0 16px 12px" }}>
        승인 전에는 외부로 발송되지 않습니다
      </div>
    </article>
  );
}

function MobileChatThread({
  messages,
  prompts,
  sendMessage,
  onAction,
  onShowSource,
}: {
  messages: ReturnType<typeof useAgentChat>["messages"];
  prompts: string[];
  sendMessage: (message: string) => Promise<void>;
  onAction: (action: NextAction) => void;
  onShowSource: (response: AgentChatResponse) => void;
}) {
  if (messages.length === 0) {
    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginTop: 14 }}>
        {prompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => void sendMessage(prompt)}
            style={{
              background: "#fff",
              border: "1px solid rgba(27,63,160,0.18)",
              borderRadius: 999,
              color: "#1B3FA0",
              cursor: "pointer",
              font: "inherit",
              fontSize: 11.5,
              fontWeight: 800,
              padding: "6px 9px",
            }}
            type="button"
          >
            {prompt}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div style={{ marginTop: 16 }}>
      <strong style={{ color: "#0F172A", fontSize: 12.5 }}>AI 반장 대화</strong>
      <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
        {messages.map((message) => {
          if (message.role === "user") {
            return (
              <div key={message.id} style={{ display: "flex", justifyContent: "flex-end" }}>
                <p style={userBubbleStyle}>{message.content}</p>
              </div>
            );
          }
          return (
            <div key={message.id} style={{ display: "flex", gap: 7 }}>
              <span style={agentAvatarStyle}>반</span>
              <div style={assistantBubbleStyle}>
                <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{message.content}</p>
                <ChatMeta
                  onAction={onAction}
                  onShowSource={onShowSource}
                  response={message.response}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChatMeta({
  response,
  onAction,
  onShowSource,
}: {
  response: AgentChatResponse;
  onAction: (action: NextAction) => void;
  onShowSource: (response: AgentChatResponse) => void;
}) {
  const firstTool = response.tool_calls[0]?.name;
  const intent = response.normalized_intent ?? response.structured_plan.intent ?? "unknown";
  const visibleActions = response.actions.filter(
    (action) => action.action_type === "request_document" || action.action_type === "create_handoff",
  );

  return (
    <div style={{ borderTop: "1px solid #E2E8F0", marginTop: 9, paddingTop: 7 }}>
      <div style={{ color: "#94A3B8", display: "flex", flexWrap: "wrap", fontSize: 10.5, fontWeight: 800, gap: 6 }}>
        <span>{response.route}</span>
        <span>{intent}</span>
        {firstTool ? <span>{firstTool}</span> : null}
        {response.approval_required ? <span style={{ color: "#B45309" }}>승인 필요</span> : null}
      </div>
      {visibleActions.length || response.sources.length ? (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
          {visibleActions.map((action) => (
            <button key={action.action_id} onClick={() => onAction(action)} style={chatActionButtonStyle} type="button">
              {action.action_type === "request_document" ? "초안 보기" : "패키지 보기"}
            </button>
          ))}
          {response.sources.length ? (
            <button onClick={() => onShowSource(response)} style={chatSourceButtonStyle} type="button">
              근거 보기
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function MobileSheet({
  children,
  title,
  onClose,
}: {
  children: ReactNode;
  title: string;
  onClose: () => void;
}) {
  return (
    <section
      style={{
        background: "#fff",
        border: "1px solid rgba(15,23,42,0.09)",
        borderRadius: 16,
        boxShadow: "0 8px 30px rgba(15,23,42,0.10)",
        marginTop: 14,
        padding: 14,
      }}
    >
      <div style={{ alignItems: "center", display: "flex", gap: 8 }}>
        <strong style={{ color: "#0F172A", fontSize: 14 }}>{title}</strong>
        <span style={{ flex: 1 }} />
        <button onClick={onClose} style={sheetCloseButtonStyle} type="button">
          닫기
        </button>
      </div>
      <div style={{ marginTop: 10 }}>{children}</div>
    </section>
  );
}

const emptyStateStyle = {
  alignItems: "center",
  color: "#64748B",
  display: "flex",
  fontSize: 13,
  justifyContent: "center",
  minHeight: 96,
  padding: 18,
} as const;

const errorStateStyle = {
  background: "#FEF2F2",
  border: "1px solid #FECACA",
  borderRadius: 12,
  color: "#B42318",
  fontSize: 12.5,
  fontWeight: 800,
  marginTop: 12,
  padding: "9px 11px",
} as const;

const cardButtonStyle = {
  background: "linear-gradient(135deg, #1B3FA0, #00BFA5)",
  border: 0,
  borderRadius: 10,
  color: "#fff",
  cursor: "pointer",
  flex: 1,
  font: "inherit",
  fontSize: 13,
  fontWeight: 900,
  padding: "10px 0",
} as const;

const userBubbleStyle = {
  background: "#1B3FA0",
  borderRadius: "16px 16px 4px 16px",
  color: "#fff",
  fontSize: 13,
  lineHeight: 1.5,
  margin: 0,
  maxWidth: "82%",
  padding: "9px 12px",
  whiteSpace: "pre-wrap",
} as const;

const agentAvatarStyle = {
  alignItems: "center",
  background: "linear-gradient(135deg, #1B3FA0, #00BFA5)",
  borderRadius: 8,
  color: "#fff",
  display: "flex",
  flexShrink: 0,
  fontSize: 11,
  fontWeight: 900,
  height: 24,
  justifyContent: "center",
  width: 24,
} as const;

const assistantBubbleStyle = {
  background: "#fff",
  border: "1px solid rgba(15,23,42,0.09)",
  borderRadius: "4px 16px 16px 16px",
  boxShadow: "0 1px 5px rgba(15,23,42,0.05)",
  color: "#0F172A",
  fontSize: 13,
  lineHeight: 1.6,
  maxWidth: "86%",
  padding: "10px 12px",
} as const;

const chatActionButtonStyle = {
  background: "#1B3FA0",
  border: 0,
  borderRadius: 999,
  color: "#fff",
  cursor: "pointer",
  font: "inherit",
  fontSize: 11.5,
  fontWeight: 900,
  padding: "6px 9px",
} as const;

const chatSourceButtonStyle = {
  background: "#fff",
  border: "1px solid rgba(27,63,160,0.24)",
  borderRadius: 999,
  color: "#1B3FA0",
  cursor: "pointer",
  font: "inherit",
  fontSize: 11.5,
  fontWeight: 900,
  padding: "5px 9px",
} as const;

const sheetTextStyle = {
  background: "#F8FAFC",
  borderRadius: 12,
  color: "#334155",
  fontSize: 12.5,
  lineHeight: 1.65,
  margin: "0 0 8px",
  padding: 10,
  whiteSpace: "pre-wrap",
} as const;

const sheetPreStyle = {
  ...sheetTextStyle,
  maxHeight: 240,
  overflow: "auto",
} as const;

const sheetNoticeStyle = {
  color: "#B45309",
  fontSize: 11.5,
  fontWeight: 900,
  margin: "8px 0 0",
} as const;

const sheetCloseButtonStyle = {
  background: "#E2E8F0",
  border: 0,
  borderRadius: 999,
  color: "#334155",
  cursor: "pointer",
  font: "inherit",
  fontSize: 11.5,
  fontWeight: 900,
  padding: "5px 9px",
} as const;
