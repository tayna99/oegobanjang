"use client";

import { useEffect, useRef } from "react";

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
  const threadRef = useRef<HTMLDivElement | null>(null);
  const { draft, error, handleSubmit, loading, messages, resetMessages, sendMessage, setDraft } = useAgentChat({
    companyId,
    date,
    workspaceId: "daily_briefing",
    activeTab: "today",
    selectedCaseId,
    selectedActionId,
  });

  useEffect(() => {
    const thread = threadRef.current;
    if (!thread) {
      return;
    }
    thread.scrollTop = thread.scrollHeight;
  }, [loading, messages]);

  return (
    <aside className="agent-chat-card">
      <div className="agent-chat-heading">
        <span className="agent-chat-avatar">반</span>
        <div>
          <p>AI 반장</p>
          <h2>데일리 브리핑 AI 반장</h2>
        </div>
        <span className="agent-chat-badge">근거 기반</span>
      </div>

      {messages.length > 0 ? (
        <div className="agent-chat-reset">
          <button disabled={loading} onClick={resetMessages} type="button">
            최신 데이터로 다시 시작
          </button>
        </div>
      ) : null}

      <div className="agent-chat-suggestions">
        {suggestionPrompts.map((prompt) => (
          <button disabled={loading} key={prompt} onClick={() => void sendMessage(prompt)} type="button">
            {prompt}
          </button>
        ))}
      </div>

      <div className="agent-chat-thread" ref={threadRef}>
        {messages.length === 0 ? (
          <div className="agent-chat-empty">
            <strong>오늘 외국인 고용 업무를 같이 확인할게요.</strong>
            <p>
              비자, 서류, 채용 준비, 행정사 전달, 판단 근거를 자연어로 물어볼 수 있습니다. 발송과 제출은
              담당자 승인 전에는 실행하지 않습니다.
            </p>
            <div className="agent-chat-empty-actions">
              <button disabled={loading} onClick={() => void sendMessage("오늘 먼저 볼 일 정리해줘")} type="button">
                오늘 먼저 볼 일
              </button>
              <button disabled={loading} onClick={() => void sendMessage("Nguyen 케이스 근거 보여줘")} type="button">
                Nguyen 근거 확인
              </button>
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <div className={message.role === "user" ? "agent-message user" : "agent-message assistant"} key={message.id}>
            {message.role === "assistant" ? <ChatAnswer content={message.content} /> : <p>{message.content}</p>}
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
      <p className="agent-chat-footnote">AI 반장은 제한된 운영 데이터와 근거를 바탕으로 답합니다. 중요한 판단은 담당자 확인이 필요합니다.</p>
    </aside>
  );
}

function ChatAnswer({ content }: { content: string }) {
  const lines = content
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\bCRITICAL\b/g, "즉시 확인")
    .replace(/\bHIGH\b/g, "우선 확인")
    .replace(/\bMEDIUM\b/g, "확인 필요")
    .replace(/\bLOW\b/g, "참고")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return <p>확인된 내용을 정리했습니다.</p>;
  }

  return (
    <div className="agent-answer-body">
      {lines.map((line, index) => {
        const isNumbered = /^\d+\.\s+/.test(line);
        const isBullet = /^[-•]\s+/.test(line);
        const cleanLine = line
          .replace(/^\d+\.\s+/, "")
          .replace(/^[-•]\s+/, "")
          .replace(/\s{2,}/g, " ");

        if (isNumbered) {
          return (
            <div className="agent-answer-case" key={`${cleanLine}_${index}`}>
              {cleanLine}
            </div>
          );
        }

        if (isBullet) {
          return (
            <div className="agent-answer-detail" key={`${cleanLine}_${index}`}>
              <span aria-hidden="true" />
              <p>{cleanLine}</p>
            </div>
          );
        }

        return <p key={`${cleanLine}_${index}`}>{cleanLine}</p>;
      })}
    </div>
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
  const visibleActions = response.actions.filter(
    (action) => action.action_type === "request_document" || action.action_type === "create_handoff",
  );
  const firstSource = response.sources[0];
  const actionByType = new Map<NextAction["action_type"], NextAction>();
  visibleActions.forEach((action) => {
    if (!actionByType.has(action.action_type)) {
      actionByType.set(action.action_type, action);
    }
  });
  const uniqueActions = Array.from(actionByType.values());
  const contactPreview = response.contact_preview;
  const chips = [
    labelRoute(response.route),
    labelIntent(response.normalized_intent ?? response.structured_plan.intent),
    response.agent_used ? labelAgent(response.agent_used) : null,
    firstSource ? "근거 확인됨" : null,
    response.approval_required ? "승인 필요" : null,
  ].filter((chip): chip is string => Boolean(chip));

  return (
    <div className="agent-chat-meta">
      <div className="agent-chat-meta-chips" aria-label="응답 상태">
        {chips.map((chip) => (
          <span data-alert={chip === "승인 필요" ? "true" : undefined} key={chip}>
            {chip}
          </span>
        ))}
      </div>
      {contactPreview?.kind === "message_draft" ? (
        <details className="agent-chat-contact-preview">
          <summary>다국어 초안 보기</summary>
          {contactPreview.korean_text ? <p>{contactPreview.korean_text}</p> : null}
          {contactPreview.translated_text ? <p>{contactPreview.translated_text}</p> : null}
        </details>
      ) : null}
      {contactPreview?.kind === "worker_reply_summary" ? (
        <details className="agent-chat-contact-preview">
          <summary>응답 요약 보기</summary>
          <p>{contactPreview.summary_ko ?? "담당자 검토용 요약을 생성했습니다."}</p>
          <p>상태 업데이트 후보 {contactPreview.status_update_candidate_count ?? 0}건</p>
        </details>
      ) : null}
      {uniqueActions.length || firstSource ? (
        <div className="agent-chat-meta-actions">
          {uniqueActions.map((action) => {
            if (action.action_type === "request_document") {
              return (
                <button key={action.action_id} onClick={() => onOpenDocumentDraft?.(action)} type="button">
                  서류 요청 초안
                </button>
              );
            }
            return (
              <button key={action.action_id} onClick={() => onOpenHandoffPreview?.(action)} type="button">
                행정사 검토 패키지
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

function labelRoute(route: string) {
  const labels: Record<string, string> = {
    agent_runtime_workflow: "업무 처리",
    daily_briefing_service: "브리핑 요약",
    rag_first_chat: "근거 기반 응답",
    unsupported: "지원 범위 확인",
  };
  return labels[route] ?? "AI 응답";
}

function labelAgent(agentUsed: string) {
  const labels: Record<string, string> = {
    visa_agent: "비자/체류 에이전트",
    multilingual_contact_agent: "다국어 에이전트",
    hiring_agent: "인력확보 에이전트",
  };
  return labels[agentUsed] ?? agentUsed;
}

function labelIntent(intent?: string | null) {
  if (!intent) {
    return null;
  }
  const labels: Record<string, string> = {
    candidate_readiness: "채용 준비",
    contact_follow_up: "컨택",
    contact_onboarding: "컨택 안내",
    document_request_message: "서류 요청",
    handoff_package: "행정사 검토",
    missing_document: "누락 서류",
    reporting_deadline: "신고기한",
    visa_expiry: "체류기간",
    worker_reply_interpretation: "응답 해석",
  };
  return labels[intent] ?? null;
}
