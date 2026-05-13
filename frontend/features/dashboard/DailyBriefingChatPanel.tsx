"use client";

import type { AgentChatResponse, NextAction } from "../../types/dailyBriefing";
import { useAgentChat } from "./useAgentChat";

type DailyBriefingChatPanelProps = {
  companyId: string;
  date: string;
  selectedCaseId?: string | null;
  selectedActionId?: string | null;
  onOpenDocumentDraft?: (action: NextAction) => void;
  onOpenHandoffPreview?: (action: NextAction) => void;
  onOpenCitation?: (citationId: string) => void;
};

const suggestionPrompts = [
  "오늘 외국인 직원 쪽에서 먼저 볼 거 있어?",
  "비자 끝나는 사람 있으면 먼저 알려줘",
  "베트남어로 여권 사본 요청 메시지 만들어줘",
  "고용변동 신고 기한 지난 케이스 있어?",
];

export function DailyBriefingChatPanel({
  companyId,
  date,
  selectedCaseId,
  selectedActionId,
  onOpenDocumentDraft,
  onOpenHandoffPreview,
  onOpenCitation,
}: DailyBriefingChatPanelProps) {
  const { draft, error, handleSubmit, loading, messages, sendMessage, setDraft } = useAgentChat({
    companyId,
    date,
    workspaceId: "daily_briefing",
    activeTab: "today",
    selectedCaseId,
    selectedActionId,
  });

  return (
    <aside className="agent-chat-card">
      <div className="agent-chat-heading">
        <span className="agent-chat-avatar">반</span>
        <div>
          <p>AI 반장</p>
          <h2>데일리 브리핑 챗봇</h2>
        </div>
        <span className="agent-chat-badge">API 연결</span>
      </div>

      <div className="agent-chat-suggestions">
        {suggestionPrompts.map((prompt) => (
          <button disabled={loading} key={prompt} onClick={() => void sendMessage(prompt)} type="button">
            {prompt}
          </button>
        ))}
      </div>

      <div className="agent-chat-thread">
        {messages.length === 0 ? (
          <div className="agent-chat-empty">
            오늘 업무, 비자, 서류, 채용, 행정사 전달, 판단 근거를 자연어로 물어볼 수 있습니다.
          </div>
        ) : null}

        {messages.map((message) => (
          <div className={message.role === "user" ? "agent-message user" : "agent-message assistant"} key={message.id}>
            <p>{message.content}</p>
            {message.role === "assistant" ? (
              <ChatMetadata
                onOpenCitation={onOpenCitation}
                onOpenDocumentDraft={onOpenDocumentDraft}
                onOpenHandoffPreview={onOpenHandoffPreview}
                response={message.response}
              />
            ) : null}
          </div>
        ))}
      </div>

      {error ? <p className="agent-chat-error">{error}</p> : null}

      <form className="agent-chat-form" onSubmit={handleSubmit}>
        <input
          disabled={loading}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="외국인 고용 업무 관련 질문..."
          value={draft}
        />
        <button disabled={loading || !draft.trim()} type="submit">
          {loading ? "확인 중" : "전송"}
        </button>
      </form>
    </aside>
  );
}

function ChatMetadata({
  response,
  onOpenDocumentDraft,
  onOpenHandoffPreview,
  onOpenCitation,
}: {
  response: AgentChatResponse;
  onOpenDocumentDraft?: (action: NextAction) => void;
  onOpenHandoffPreview?: (action: NextAction) => void;
  onOpenCitation?: (citationId: string) => void;
}) {
  const tool = response.tool_calls[0];
  const visibleActions = response.actions.filter(
    (action) => action.action_type === "request_document" || action.action_type === "create_handoff",
  );
  const firstSource = response.sources[0];

  return (
    <div className="agent-chat-meta">
      <div>
        <span>{response.route}</span>
        <span>{response.normalized_intent ?? response.structured_plan.intent ?? "unknown"}</span>
        {tool ? <span>{tool.name}</span> : null}
        {response.approval_required ? <strong>승인 필요</strong> : null}
      </div>
      {visibleActions.length || firstSource ? (
        <div className="agent-chat-meta-actions">
          {visibleActions.map((action) => {
            if (action.action_type === "request_document") {
              return (
                <button key={action.action_id} onClick={() => onOpenDocumentDraft?.(action)} type="button">
                  서류 요청 초안
                </button>
              );
            }
            return (
              <button key={action.action_id} onClick={() => onOpenHandoffPreview?.(action)} type="button">
                행정사 패키지
              </button>
            );
          })}
          {firstSource ? (
            <button onClick={() => onOpenCitation?.(firstSource.citation_id)} type="button">
              근거 보기
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
