"use client";

import { FormEvent, useMemo, useState } from "react";

import { sendAgentChatMessage } from "../../lib/api";
import type { AgentChatResponse, NextAction } from "../../types/dailyBriefing";

type ChatMessage =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; content: string; response: AgentChatResponse };

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
  "외국인등록증이나 여권 사본 안 받은 사람 있어?",
  "이 건 행정사한테 넘기려면 뭐 묶어야 돼?",
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionId = useMemo(() => `daily_briefing_chat_${Date.now()}`, []);

  async function sendMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) {
      return;
    }

    setMessages((current) => [
      ...current,
      { id: `user_${Date.now()}`, role: "user", content: trimmed },
    ]);
    setDraft("");
    setError(null);
    setLoading(true);

    try {
      const response = await sendAgentChatMessage({
        message: trimmed,
        companyId,
        date,
        workspaceId: "daily_briefing",
        activeTab: "today",
        selectedCaseId: selectedCaseId ?? undefined,
        selectedActionId: selectedActionId ?? undefined,
        sessionId,
      });
      setMessages((current) => [
        ...current,
        {
          id: `assistant_${Date.now()}`,
          role: "assistant",
          content: response.answer,
          response,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI 반장 호출에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(draft);
  }

  return (
    <aside className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.25em] text-cyan-200">AI 반장</p>
          <h2 className="mt-2 text-2xl font-black">데일리 브리핑 챗봇</h2>
        </div>
        <span className="rounded-full bg-cyan-400/15 px-3 py-1 text-xs font-bold text-cyan-100">
          API 연결
        </span>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {suggestionPrompts.map((prompt) => (
          <button
            className="rounded-full border border-white/15 px-3 py-2 text-xs font-bold text-slate-100 disabled:opacity-50"
            disabled={loading}
            key={prompt}
            onClick={() => void sendMessage(prompt)}
            type="button"
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="mt-5 max-h-[420px] space-y-3 overflow-auto pr-1">
        {messages.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-slate-200">
            오늘 업무, 비자, 서류, 채용, 행정사 전달, 판단 근거를 자연어로 물어볼 수 있습니다.
          </div>
        ) : null}

        {messages.map((message) => (
          <div
            className={
              message.role === "user"
                ? "ml-auto max-w-[85%] rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-bold text-slate-950"
                : "max-w-[92%] rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-900"
            }
            key={message.id}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
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

      {error ? <p className="mt-4 text-sm font-semibold text-red-200">{error}</p> : null}

      <form className="mt-5 flex gap-2" onSubmit={handleSubmit}>
        <input
          className="min-w-0 flex-1 rounded-full border border-white/15 bg-white px-4 py-3 text-sm text-slate-950 outline-none"
          onChange={(event) => setDraft(event.target.value)}
          placeholder="외국인 고용 업무 관련 질문..."
          value={draft}
        />
        <button
          className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-black text-slate-950 disabled:opacity-50"
          disabled={loading || !draft.trim()}
          type="submit"
        >
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
    <div className="mt-3 space-y-3 border-t border-slate-200 pt-3 text-xs font-bold text-slate-500">
      <div className="flex flex-wrap gap-2">
        <span>{response.route}</span>
        <span>{response.normalized_intent ?? response.structured_plan.intent ?? "unknown"}</span>
        {tool ? <span>{tool.name}</span> : null}
        {response.approval_required ? <span>승인 필요</span> : null}
      </div>
      {visibleActions.length || firstSource ? (
        <div className="flex flex-wrap gap-2">
          {visibleActions.map((action) => {
            if (action.action_type === "request_document") {
              return (
                <button
                  className="rounded-full bg-slate-950 px-3 py-1.5 text-xs font-black text-white"
                  key={action.action_id}
                  onClick={() => onOpenDocumentDraft?.(action)}
                  type="button"
                >
                  서류 요청 초안
                </button>
              );
            }
            return (
              <button
                className="rounded-full bg-slate-950 px-3 py-1.5 text-xs font-black text-white"
                key={action.action_id}
                onClick={() => onOpenHandoffPreview?.(action)}
                type="button"
              >
                행정사 패키지
              </button>
            );
          })}
          {firstSource ? (
            <button
              className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-black text-slate-700"
              onClick={() => onOpenCitation?.(firstSource.citation_id)}
              type="button"
            >
              근거 보기
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
