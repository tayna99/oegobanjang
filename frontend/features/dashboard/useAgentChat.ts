"use client";

import { FormEvent, useMemo, useState } from "react";

import { sendAgentChatMessage } from "../../lib/api";
import type { AgentChatResponse } from "../../types/dailyBriefing";

export type AgentChatMessage =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; content: string; response: AgentChatResponse };

export type AgentChatContext = {
  companyId: string;
  date?: string;
  workspaceId: string;
  activeTab?: string;
  selectedCaseId?: string | null;
  selectedActionId?: string | null;
};

export function useAgentChat(context: AgentChatContext) {
  const [messages, setMessages] = useState<AgentChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionId = useMemo(() => `${context.workspaceId}_chat_${Date.now()}`, [context.workspaceId]);

  async function sendMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) {
      return;
    }

    setMessages([{ id: `user_${Date.now()}`, role: "user", content: trimmed }]);
    setDraft("");
    setError(null);
    setLoading(true);

    try {
      const response = await sendAgentChatMessage({
        message: trimmed,
        companyId: context.companyId,
        date: context.date,
        workspaceId: context.workspaceId,
        activeTab: context.activeTab ?? "today",
        selectedCaseId: context.selectedCaseId ?? undefined,
        selectedActionId: context.selectedActionId ?? undefined,
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

  function resetMessages() {
    setMessages([]);
    setDraft("");
    setError(null);
  }

  return {
    draft,
    error,
    handleSubmit,
    loading,
    messages,
    resetMessages,
    sendMessage,
    setDraft,
  };
}
