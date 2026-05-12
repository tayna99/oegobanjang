"use client";

import { FormEvent, useMemo, useState } from "react";

import { sendAgentChatMessage } from "../../lib/api";
import type { AgentChatResponse } from "../../types/dailyBriefing";

type ChatMessage =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; content: string; response: AgentChatResponse };

const suggestionPrompts = [
  "비자 관련 업무가 뭐였어?",
  "서류 누락 일괄 점검",
  "신규 외국인 근로자 채용 준비",
  "감사 로그/근거 재현 케이스",
];

export function DailyBriefingChatPanel({ companyId }: { companyId: string }) {
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
        activeTab: "today",
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
      setError(err instanceof Error ? err.message : "Agent chat failed");
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
          <h2 className="mt-2 text-2xl font-black">Daily Briefing chat</h2>
        </div>
        <span className="rounded-full bg-cyan-400/15 px-3 py-1 text-xs font-bold text-cyan-100">
          API connected
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
            오늘 업무, 비자, 서류, 채용, 근거 기록을 물어볼 수 있습니다.
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
            {message.role === "assistant" ? <ChatMetadata response={message.response} /> : null}
          </div>
        ))}
      </div>

      {error ? <p className="mt-4 text-sm font-semibold text-red-200">{error}</p> : null}

      <form className="mt-5 flex gap-2" onSubmit={handleSubmit}>
        <input
          className="min-w-0 flex-1 rounded-full border border-white/15 bg-white px-4 py-3 text-sm text-slate-950 outline-none"
          onChange={(event) => setDraft(event.target.value)}
          placeholder="외고 업무 관련 질문..."
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

function ChatMetadata({ response }: { response: AgentChatResponse }) {
  const tool = response.tool_calls[0];

  return (
    <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-200 pt-3 text-xs font-bold text-slate-500">
      <span>{response.structured_plan.intent ?? "unknown"}</span>
      <span>{response.route}</span>
      <span>{response.latency_mode}</span>
      {tool ? <span>{tool.name}: {tool.result_count}건</span> : null}
      {response.approval_required ? <span>approval required</span> : null}
    </div>
  );
}
