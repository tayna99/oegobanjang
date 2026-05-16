import { FileText, MessageSquare, Paperclip, Pencil, Send, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import React, { useEffect, useMemo, useState } from "react";

import { Button } from "../ui";
import styles from "../PcShell.module.css";
import type { PcViewProps } from "./today";

const COMPANY_ID = "550e8400-e29b-41d4-a716-446655440001";

type WorkerOption = {
  id: string;
  name: string;
  full_name?: string;
  nationality?: string;
  language_code: string;
  language_label: string;
  email?: string;
  visa_type?: string;
};

type ContactAttachment = {
  id: string;
  filename: string;
  mime_type?: string;
  size?: string;
  doc_type?: string | null;
  doc_status?: string | null;
};

type ContactMessage = {
  id: string;
  worker_id: string;
  direction: "OUTBOUND" | "INBOUND";
  source: "LANGCHAIN" | "PORTAL" | "MANAGER" | "EXPERT_REVIEW" | "EXPERT_REPLY" | string;
  language_code: string;
  body_original: string;
  body_ko: string;
  status: string;
  sender_email?: string;
  received_at?: string;
  created_at?: string;
  attachments: ContactAttachment[];
};

type ContactThread = {
  id: string;
  channel?: "portal" | "expert" | string;
  worker: WorkerOption;
  title: string;
  status: string;
  message_type?: string | null;
  last_message_at?: string;
  last_message_preview?: string;
  message_count: number;
  messages?: ContactMessage[];
};

export function ContactView({ onAction }: PcViewProps = {}) {
  const searchParams = useSearchParams();
  const [workers, setWorkers] = useState<WorkerOption[]>([]);
  const [threads, setThreads] = useState<ContactThread[]>([]);
  const [expertThreads, setExpertThreads] = useState<ContactThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<ContactThread | null>(null);
  const [activeMessageTab, setActiveMessageTab] = useState<"worker" | "expert">("worker");
  const [selectedWorkerId, setSelectedWorkerId] = useState("");
  const [languageView, setLanguageView] = useState<"worker" | "ko">("worker");
  const [loading, setLoading] = useState(true);
  const [handoffNotice, setHandoffNotice] = useState("");
  const [handoffDraftText, setHandoffDraftText] = useState("");
  const [handoffEditing, setHandoffEditing] = useState(false);
  const [handoffSent, setHandoffSent] = useState(false);
  const [editingMessage, setEditingMessage] = useState<ContactMessage | null>(null);
  const [editKo, setEditKo] = useState("");
  const [editOriginal, setEditOriginal] = useState("");
  const [expertDraft, setExpertDraft] = useState("");
  const [expertFiles, setExpertFiles] = useState<File[]>([]);
  const [expertSending, setExpertSending] = useState(false);
  const requestedWorkerId = searchParams.get("worker_id");
  const requestedThreadId = searchParams.get("thread_id");
  const requestedActionLabel = searchParams.get("label");

  const selectedWorker = useMemo(
    () => workers.find((worker) => worker.id === selectedWorkerId) ?? workers[0],
    [selectedWorkerId, workers],
  );

  useEffect(() => {
    void loadInitial();
  }, []);

  useEffect(() => {
    if (!selectedThread?.id) return;
    const timer = window.setInterval(() => {
      void refreshSelectedThread(selectedThread.id);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [selectedThread?.id]);

  useEffect(() => {
    const visible = activeMessageTab === "worker" ? threads : expertThreads;
    if (visible.length === 0) return;
    if (requestedThreadId) {
      const found = visible.find((thread) => thread.id === requestedThreadId);
      if (found) void selectThread(found.id);
      return;
    }
    if (requestedWorkerId) {
      const found = visible.find((thread) => thread.worker.id === requestedWorkerId);
      if (found) void selectThread(found.id);
    }
  }, [requestedThreadId, requestedWorkerId, threads, expertThreads, activeMessageTab]);

  async function loadInitial() {
    setLoading(true);
    try {
      const [workerResponse, threadResponse, expertThreadResponse] = await Promise.all([
        fetch(`/api/v1/contact/workers?company_id=${encodeURIComponent(COMPANY_ID)}`, { cache: "no-store" }),
        fetch(`/api/v1/contact/threads?company_id=${encodeURIComponent(COMPANY_ID)}&channel=portal`, { cache: "no-store" }),
        fetch(`/api/v1/contact/threads?company_id=${encodeURIComponent(COMPANY_ID)}&channel=expert`, { cache: "no-store" }),
      ]);
      const workerData = await workerResponse.json();
      const threadData = await threadResponse.json();
      const expertThreadData = await expertThreadResponse.json();
      const nextWorkers = uniqueWorkers(workerData.workers ?? []);
      const nextThreads = threadData.threads ?? [];
      const nextExpertThreads = expertThreadData.threads ?? [];
      setWorkers(nextWorkers);
      setThreads(nextThreads);
      setExpertThreads(nextExpertThreads);
      setSelectedWorkerId(requestedWorkerId || nextWorkers[0]?.id || "");
      if (nextThreads.length > 0) await selectThread(nextThreads[0].id);
      else setSelectedThread(null);
    } finally {
      setLoading(false);
    }
  }

  async function selectThread(threadId: string) {
    const response = await fetch(`/api/v1/contact/threads/${threadId}`, { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    setSelectedThread(data);
    setSelectedWorkerId(data.worker?.id ?? "");
    setLanguageView("worker");
    setHandoffNotice("");
    setHandoffEditing(false);
    setHandoffSent(hasExpertReviewRequest(data, expertThreads));
    if (data.worker?.name === "Nguyen V.") {
      setHandoffDraftText(buildExpertMessage("Nguyen V."));
    } else {
      setHandoffDraftText("");
    }
  }

  async function refreshSelectedThread(threadId: string) {
    const response = await fetch(`/api/v1/contact/threads/${threadId}`, { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    setSelectedThread(data);
    setSelectedWorkerId(data.worker?.id ?? "");
    setHandoffSent(hasExpertReviewRequest(data, expertThreads));
  }

  async function switchMessageTab(nextTab: "worker" | "expert") {
    setActiveMessageTab(nextTab);
    setHandoffNotice("");
    const nextThreads = nextTab === "worker" ? threads : expertThreads;
    if (nextThreads.length > 0) {
      await selectThread(nextThreads[0].id);
      return;
    }
    setSelectedThread(null);
  }

  function openMessageEdit(message: ContactMessage) {
    setEditingMessage(message);
    setEditKo(message.body_ko);
    setEditOriginal(message.body_original);
  }

  async function submitMessageEdit() {
    if (!editingMessage) return;
    const bodyKo = editKo.trim();
    if (!bodyKo) return;
    const response = await fetch(`/api/v1/contact/messages/${encodeURIComponent(editingMessage.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        body_ko: bodyKo,
        body_original: editOriginal.trim() || bodyKo,
      }),
    });
    if (!response.ok) return;
    const savedThread = await response.json() as ContactThread;
    setSelectedThread(savedThread);
    updateThreadList(savedThread);
    setEditingMessage(null);
    setEditKo("");
    setEditOriginal("");
  }

  function updateThreadList(savedThread: ContactThread) {
    const setter = savedThread.channel === "expert" ? setExpertThreads : setThreads;
    setter((items) =>
      items.map((thread) =>
        thread.id === savedThread.id
          ? {
              ...thread,
              last_message_preview: savedThread.last_message_preview,
              message_count: savedThread.message_count,
              status: savedThread.status,
            }
          : thread,
      ),
    );
  }

  async function sendExpertReviewRequest() {
    if (!selectedThread) return;
    const workerName = selectedThread.worker.name ?? "Nguyen V.";
    const message = handoffDraftText.trim() || buildExpertMessage(workerName);
    const response = await fetch("/api/v1/contact/expert-threads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        worker_id: selectedThread.worker.id,
        company_id: COMPANY_ID,
        body_ko: message,
      }),
    });
    if (!response.ok) return;
    const savedThread = await response.json() as ContactThread;
    setExpertThreads((items) => {
      const exists = items.some((thread) => thread.id === savedThread.id);
      if (exists) {
        return items.map((thread) => thread.id === savedThread.id ? savedThread : thread);
      }
      return [savedThread, ...items];
    });
    setActiveMessageTab("expert");
    setSelectedThread(savedThread);
    setSelectedWorkerId(savedThread.worker.id);
    setHandoffNotice("행정사 메시지 관리에 검토 요청이 도착했습니다.");
    setHandoffEditing(false);
    setHandoffSent(true);
  }

  async function sendAdminExpertMessage() {
    if (!selectedThread || activeMessageTab !== "expert") return;
    const body = expertDraft.trim();
    if (!body && expertFiles.length === 0) return;
    setExpertSending(true);
    try {
      const formData = new FormData();
      formData.append("body_ko", body || "첨부파일을 전달합니다.");
      formData.append("body_original", body || "첨부파일을 전달합니다.");
      formData.append("language_code", "ko");
      formData.append("source", "MANAGER");
      formData.append("status", "담당자 입력");
      formData.append("direction", "OUTBOUND");
      expertFiles.forEach((file) => formData.append("files", file));
      const response = await fetch(`/api/v1/contact/threads/${encodeURIComponent(selectedThread.id)}/messages/form`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) return;
      const savedThread = await response.json() as ContactThread;
      setSelectedThread(savedThread);
      updateThreadList(savedThread);
      setExpertDraft("");
      setExpertFiles([]);
    } finally {
      setExpertSending(false);
    }
  }

  const detailWorker = selectedThread?.worker;
  const messages = selectedThread?.messages ?? [];
  const visibleThreads = activeMessageTab === "worker" ? threads : expertThreads;
  const workerLanguageLabel = detailWorker?.language_label ?? selectedWorker?.language_label ?? "원문";
  const canShowHandoffDraft = activeMessageTab === "worker" && Boolean(detailWorker?.name === "Nguyen V." || selectedWorker?.name === "Nguyen V.");

  return (
    <div className={styles.stack}>
      <div className={styles.pageHead}>
        <div>
          <div className={styles.subtle}>메시지 관리</div>
          <h1 className={styles.headline}>메시지 관리</h1>
          <p className={styles.subtle}>근로자·행정사와 주고받은 메시지를 확인하고, 답변 전 보낸 메시지만 수정합니다.</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px minmax(0, 1fr)", gap: 18, alignItems: "start" }}>
        <aside className={styles.contactList}>
          <div style={{ padding: "12px 14px", borderBottom: "1px solid #E5EAF3", display: "grid", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B" }}>메시지 목록 · {visibleThreads.length}건</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              <button onClick={() => switchMessageTab("worker")} style={activeMessageTab === "worker" ? activeTabButtonStyle : tabButtonStyle} type="button">근로자</button>
              <button onClick={() => switchMessageTab("expert")} style={activeMessageTab === "expert" ? activeTabButtonStyle : tabButtonStyle} type="button">행정사</button>
            </div>
          </div>

          {loading ? (
            <div style={emptyStyle}>불러오는 중입니다.</div>
          ) : visibleThreads.length === 0 ? (
            <div style={emptyStyle}>메시지가 없습니다.</div>
          ) : (
            visibleThreads.map((thread) => {
              const selected = selectedThread?.id === thread.id;
              return (
                <button
                  key={thread.id}
                  className={styles.contactItem}
                  onClick={() => void selectThread(thread.id)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    background: selected ? "#EFF6FF" : "transparent",
                    border: 0,
                    borderLeft: selected ? "3px solid #2563EB" : "3px solid transparent",
                    cursor: "pointer",
                  }}
                  type="button"
                >
                  <span className={styles.workerAvatar} style={{ flexShrink: 0 }}>{thread.worker.name.slice(0, 1)}</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
                      <strong style={{ fontSize: 13.5 }}>{activeMessageTab === "expert" ? thread.title : thread.worker.name}</strong>
                      <span style={miniBadge}>{thread.worker.language_code.toUpperCase()}</span>
                    </div>
                    <div className={styles.subtle} style={{ fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {thread.last_message_preview || thread.title}
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 7 }}>
                      <span style={statusBadge(thread.status)}>{thread.status}</span>
                      <span className={styles.subtle} style={{ fontSize: 11 }}>{thread.message_count}건</span>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </aside>

        <section className={styles.document} style={{ minHeight: 720, padding: 0, overflow: "hidden" }}>
          {selectedThread ? (
            <div style={{ display: "grid", gridTemplateRows: activeMessageTab === "expert" ? "auto minmax(0, 1fr) auto" : "auto minmax(0, 1fr)", minHeight: 720 }}>
              <div style={{ padding: 20, borderBottom: "1px solid #E2E8F0" }}>
                {requestedActionLabel ? (
                  <div style={{ ...noticeStyle, marginBottom: 14 }}>
                    오늘 할 일에서 이동: {detailWorker?.name ?? selectedWorker?.name ?? "근로자"} · {requestedActionLabel}
                  </div>
                ) : null}
                <div className={styles.pageHead} style={{ marginBottom: 0 }}>
                  <div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                      <MessageSquare size={17} color="#2563EB" />
                      <h2 style={{ margin: 0, fontSize: 19 }}>{detailWorker?.name ?? "근로자"}</h2>
                    </div>
                    <p className={styles.subtle} style={{ margin: 0 }}>
                      {activeMessageTab === "expert" ? "행정사 대화" : `${detailWorker?.nationality ?? "-"} · ${detailWorker?.visa_type ?? "-"} · ${detailWorker?.email ?? "이메일 없음"}`}
                    </p>
                    {handoffNotice ? <p style={{ ...documentReviewNoticeStyle, marginBottom: 0 }}>{handoffNotice}</p> : null}
                  </div>
                  <div className={styles.buttonRow}>
                    {activeMessageTab === "worker" ? (
                      <>
                        <button type="button" onClick={() => setLanguageView("worker")} style={languageView === "worker" ? activeLangButton : langButton}>
                          {workerLanguageLabel}
                        </button>
                        <button type="button" onClick={() => setLanguageView("ko")} style={languageView === "ko" ? activeLangButton : langButton}>
                          한국어
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", alignContent: "end", gap: 14, padding: 20, background: "#F8FAFC" }}>
                <div style={noticeStyle}>
                  관리자가 입력한 메시지는 이 화면의 대화에 먼저 추가됩니다. 실제 외부 발송은 별도 승인 흐름에서 처리합니다.
                </div>
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    canEdit={canEditMessage(messages, message)}
                    languageView={languageView}
                    message={message}
                    onAccepted={() => void refreshSelectedThread(selectedThread.id)}
                    onEdit={() => openMessageEdit(message)}
                    workerLanguageLabel={workerLanguageLabel}
                  />
                ))}
                {canShowHandoffDraft && handoffDraftText && !handoffSent ? (
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={handoffBubbleStyle}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
                        <strong style={{ fontSize: 13 }}>행정사 검토 요청 초안</strong>
                        <span className={styles.subtle} style={{ fontSize: 11 }}>서류 승인 후 다음 단계</span>
                      </div>
                      {handoffEditing ? (
                        <textarea
                          spellCheck={false}
                          value={handoffDraftText}
                          onChange={(event) => setHandoffDraftText(event.target.value)}
                          style={{ ...composerTextareaStyle, minHeight: 180, width: "100%" }}
                        />
                      ) : (
                        <div style={{ whiteSpace: "pre-line", lineHeight: 1.75, fontSize: 14.5 }}>{handoffDraftText}</div>
                      )}
                      <div className={styles.buttonRow} style={{ justifyContent: "flex-end", marginTop: 12 }}>
                        <Button variant="secondary" onClick={() => setHandoffEditing((value) => !value)}>
                          {handoffEditing ? "수정 완료" : "내용 수정"}
                        </Button>
                        <Button disabled={!handoffDraftText.trim()} onClick={sendExpertReviewRequest}>
                          <Send size={15} /> 행정사에 검토 요청
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>

              {activeMessageTab === "expert" ? (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void sendAdminExpertMessage();
                  }}
                  style={expertComposerStyle}
                >
                  <div style={filePreviewRowStyle}>
                    {expertFiles.length === 0 ? (
                      <span className={styles.subtle} style={{ fontSize: 12 }}>첨부파일 없음</span>
                    ) : (
                      expertFiles.map((file) => (
                        <span key={`${file.name}-${file.size}`} style={fileChipStyle}>
                          <FileText size={13} /> {file.name}
                          <button
                            aria-label={`${file.name} 제거`}
                            onClick={() => setExpertFiles((items) => items.filter((item) => item !== file))}
                            style={removeFileButtonStyle}
                            type="button"
                          >
                            <X size={12} />
                          </button>
                        </span>
                      ))
                    )}
                  </div>
                  <div style={expertComposerRowStyle}>
                    <label style={attachButtonStyle}>
                      <Paperclip size={15} /> 첨부
                      <input
                        multiple
                        onChange={(event) => setExpertFiles(Array.from(event.target.files ?? []))}
                        style={{ display: "none" }}
                        type="file"
                      />
                    </label>
                    <textarea
                      aria-label="행정사에게 보낼 메시지"
                      onChange={(event) => setExpertDraft(event.target.value)}
                      placeholder="행정사에게 보낼 메시지를 입력하세요"
                      style={expertMessageTextareaStyle}
                      value={expertDraft}
                    />
                    <button
                      disabled={expertSending || (!expertDraft.trim() && expertFiles.length === 0)}
                      style={expertSendButtonStyle(expertSending || (!expertDraft.trim() && expertFiles.length === 0))}
                      type="submit"
                    >
                      <Send size={15} /> 전송
                    </button>
                  </div>
                </form>
              ) : null}

            </div>
          ) : (
            <div style={emptyDetailStyle}>
              <MessageSquare size={28} color="#94A3B8" />
              <strong style={{ display: "block", marginTop: 10, color: "#334155" }}>메시지가 없습니다.</strong>
              <div style={{ marginTop: 6 }}>메시지를 생성하거나 메일을 확인하면 대화 내용이 여기에 표시됩니다.</div>
            </div>
          )}
        </section>
      </div>

      {editingMessage ? (
        <div style={overlayStyle}>
          <div style={composerStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
              <div>
                <div className={styles.subtle} style={{ fontSize: 12 }}>답변 전 메시지 수정</div>
                <h2 style={{ margin: "4px 0 0", fontSize: 20 }}>메시지 수정</h2>
              </div>
              <button aria-label="닫기" onClick={() => setEditingMessage(null)} style={closeButtonStyle} type="button">×</button>
            </div>

            <label style={fieldLabelStyle}>
              한국어
              <textarea spellCheck={false} value={editKo} onChange={(event) => setEditKo(event.target.value)} style={{ ...composerTextareaStyle, minHeight: 150 }} />
            </label>

            <label style={fieldLabelStyle}>
              원문/번역
              <textarea spellCheck={false} value={editOriginal} onChange={(event) => setEditOriginal(event.target.value)} style={{ ...composerTextareaStyle, minHeight: 150 }} />
            </label>

            <div style={noticeStyle}>
              아직 답변이 붙지 않은 발신 메시지만 수정할 수 있습니다. 답변이 도착한 메시지는 이력 보존을 위해 수정하지 않습니다.
            </div>

            <div className={styles.buttonRow} style={{ justifyContent: "flex-end" }}>
              <Button variant="secondary" onClick={() => setEditingMessage(null)}>취소</Button>
              <Button disabled={!editKo.trim()} onClick={() => void submitMessageEdit()}>
                수정 저장
              </Button>
            </div>
          </div>
        </div>
      ) : null}

    </div>
  );
}

function uniqueWorkers(workers: WorkerOption[]) {
  const seen = new Set<string>();
  return workers.filter((worker) => {
    const key = worker.email?.trim().toLowerCase()
      || `${worker.full_name || worker.name}:${worker.nationality || ""}:${worker.visa_type || ""}`.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function hasExpertReviewRequest(thread: ContactThread, expertThreads: ContactThread[]) {
  if ((thread.messages ?? []).some((message) => message.source === "EXPERT_REVIEW")) return true;
  return expertThreads.some((expertThread) => expertThread.worker.id === thread.worker.id && (expertThread.message_count ?? 0) > 0);
}

function canEditMessage(messages: ContactMessage[], target: ContactMessage) {
  if (target.direction !== "OUTBOUND") return false;
  if (target.id.startsWith("expert-review-mirror-")) return false;
  const index = messages.findIndex((message) => message.id === target.id);
  if (index < 0) return false;
  return !messages.slice(index + 1).some((message) => message.direction === "INBOUND");
}

function MessageBubble({
  canEdit,
  message,
  languageView,
  onAccepted,
  onEdit,
  workerLanguageLabel,
}: {
  canEdit: boolean;
  message: ContactMessage;
  languageView: "worker" | "ko";
  onAccepted: () => void;
  onEdit: () => void;
  workerLanguageLabel: string;
}) {
  const outbound = message.direction === "OUTBOUND";
  const body = languageView === "ko" ? message.body_ko : message.body_original;
  const [reviewMessage, setReviewMessage] = useState("");

  async function acceptDocument(docType: string) {
    setReviewMessage("");
    const response = await fetch(`/api/v1/documents/worker-requests/${encodeURIComponent(message.worker_id)}/${encodeURIComponent(docType)}/accept`, {
      method: "POST",
    });
    if (response.ok) {
      setReviewMessage("서류가 승인 처리됐습니다. 행정사 검토 요청 초안을 확인할 수 있습니다.");
      window.dispatchEvent(new Event("workbridge-daily-briefing-refresh"));
      window.setTimeout(onAccepted, 600);
      return;
    }
    const error = await response.json().catch(() => null);
    setReviewMessage(error?.detail || "서류 승인 처리에 실패했습니다.");
  }

  async function rejectDocument(docType: string) {
    const reason = window.prompt("보완 요청 사유를 입력해 주세요.", "파일 식별이 어렵거나 보완이 필요합니다.");
    if (reason === null) return;
    setReviewMessage("");
    const response = await fetch(`/api/v1/documents/worker-requests/${encodeURIComponent(message.worker_id)}/${encodeURIComponent(docType)}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (response.ok) {
      setReviewMessage("보완 요청 메시지를 근로자에게 다시 보냈습니다.");
      window.dispatchEvent(new Event("workbridge-daily-briefing-refresh"));
      window.setTimeout(onAccepted, 600);
      return;
    }
    const error = await response.json().catch(() => null);
    setReviewMessage(error?.detail || "보완 요청 처리에 실패했습니다.");
  }

  return (
    <div style={{ display: "flex", justifyContent: outbound ? "flex-end" : "flex-start" }}>
      <div style={{
        width: "min(680px, 82%)",
        border: outbound ? "1px solid #BFDBFE" : "1px solid #A7F3D0",
        borderRadius: 14,
        background: outbound ? "#EFF6FF" : "#F0FDFA",
        padding: 18,
        color: "#0F172A",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
          <strong style={{ fontSize: 13 }}>{messageLabel(message, outbound)}</strong>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {canEdit ? (
              <button onClick={onEdit} style={editMessageButtonStyle} type="button">
                <Pencil size={12} /> 수정
              </button>
            ) : null}
            <span className={styles.subtle} style={{ fontSize: 11 }}>{languageView === "ko" ? "한국어" : workerLanguageLabel} · {message.status}</span>
          </div>
        </div>
        <div style={{ whiteSpace: "pre-line", lineHeight: 1.75, fontSize: 14.5 }}>{body}</div>
        {message.attachments.length > 0 ? (
          <div style={{ display: "grid", gap: 8, marginTop: 14 }}>
            {message.attachments.map((attachment) => (
              <div key={attachment.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 10px", borderRadius: 10, background: "#fff", border: "1px solid #E5EAF3" }}>
                <FileText size={15} color="#2563EB" />
                <a href={`/api/v1/documents/attachments/${encodeURIComponent(attachment.id)}/download`} style={attachmentLinkStyle}>{attachment.filename}</a>
                <span className={styles.subtle} style={{ fontSize: 12 }}>{attachment.size}</span>
                {!outbound && attachment.doc_type && attachment.doc_status === "SUBMITTED" ? (
                  <div style={documentReviewActionsStyle}>
                    <button onClick={() => void acceptDocument(attachment.doc_type || "")} style={confirmDocumentButtonStyle} type="button">승인</button>
                    <button onClick={() => void rejectDocument(attachment.doc_type || "")} style={rejectDocumentButtonStyle} type="button">보완 요청</button>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
        {reviewMessage ? <div style={documentReviewNoticeStyle}>{reviewMessage}</div> : null}
      </div>
    </div>
  );
}

function messageLabel(message: ContactMessage, outbound: boolean) {
  if (message.source === "EXPERT_REPLY") return "행정사 답변";
  if (!outbound) return "근로자 포털 응답";
  if (message.source === "MANAGER") return "관리자 입력";
  if (message.source === "EXPERT_REVIEW") return "행정사 검토 요청";
  return "AI 초안";
}

function buildExpertMessage(workerName: string) {
  return `${workerName}님은 E-9 근로자이며, 체류만료일은 2026-05-10로 현재 만료일이 지난 상태입니다.\n\n이전에 여권 사본이 누락되어 근로자에게 요청했고, 근로자가 포털로 여권 사본을 제출했습니다.\n관리자는 제출 파일을 확인해 여권 사본 상태를 승인 완료로 처리했습니다.\n\n현재 확보된 자료:\n- 여권 사본: 제출 및 관리자 확인 완료\n- 근로자 기본 정보: ${workerName} / Vietnam / E-9\n- 사업장: 삼성전자 부산공장\n- 계약종료일: 2027-06-01\n\n검토 요청 사항:\n1. 체류만료일이 지난 상태에서 우선 확인해야 할 절차와 리스크\n2. 여권 사본 외에 추가로 필요한 서류\n3. 외국인등록증 사본, 표준근로계약서, 고용 관련 서류의 보완 필요 여부\n4. 담당자가 행정사 검토 전 추가로 확인해야 할 정보\n5. 이후 진행 가능 일정과 주의사항\n\n본 요청은 행정사 검토용이며, 정부 포털 제출이나 대외 발송은 진행하지 않습니다.\n최종 판단과 제출 가능 여부는 행정사 검토 후 담당자가 확인하겠습니다.`;
}

const attachmentLinkStyle: React.CSSProperties = {
  color: "#1D4ED8",
  fontSize: 13,
  fontWeight: 900,
  textDecoration: "underline",
  textUnderlineOffset: 2,
};

const documentReviewActionsStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  marginLeft: "auto",
};

const documentReviewNoticeStyle: React.CSSProperties = {
  marginTop: 10,
  padding: "8px 10px",
  borderRadius: 10,
  background: "#F8FAFC",
  border: "1px solid #E2E8F0",
  color: "#334155",
  fontSize: 12.5,
  fontWeight: 800,
};

const confirmDocumentButtonStyle: React.CSSProperties = {
  minHeight: 28,
  border: "1px solid #BBF7D0",
  borderRadius: 8,
  background: "#ECFDF5",
  color: "#047857",
  padding: "0 9px",
  fontSize: 12,
  fontWeight: 900,
  cursor: "pointer",
};

const rejectDocumentButtonStyle: React.CSSProperties = {
  minHeight: 28,
  border: "1px solid #FED7AA",
  borderRadius: 8,
  background: "#FFF7ED",
  color: "#C2410C",
  padding: "0 9px",
  fontSize: 12,
  fontWeight: 900,
  cursor: "pointer",
};

const editMessageButtonStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  minHeight: 26,
  border: "1px solid #BFDBFE",
  borderRadius: 8,
  background: "#fff",
  color: "#1D4ED8",
  padding: "0 9px",
  fontSize: 12,
  fontWeight: 900,
  cursor: "pointer",
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 50,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
  background: "rgba(15, 23, 42, 0.28)",
};

const composerStyle: React.CSSProperties = {
  width: "min(460px, 100%)",
  borderRadius: 14,
  border: "1px solid #D8E0EC",
  background: "#fff",
  boxShadow: "0 22px 70px rgba(15, 23, 42, 0.18)",
  padding: 22,
  display: "grid",
  gap: 16,
};

const closeButtonStyle: React.CSSProperties = {
  width: 32,
  height: 32,
  borderWidth: 1,
  borderStyle: "solid",
  borderColor: "#E5EAF3",
  borderRadius: 8,
  background: "#fff",
  color: "#64748B",
  cursor: "pointer",
  fontSize: 20,
  lineHeight: 1,
};

const fieldLabelStyle: React.CSSProperties = {
  display: "grid",
  gap: 7,
  color: "#334155",
  fontSize: 12.5,
  fontWeight: 800,
};

const emptyStyle: React.CSSProperties = {
  padding: 22,
  color: "#64748B",
  fontSize: 13,
  textAlign: "center",
};

const emptyDetailStyle: React.CSSProperties = {
  border: "1px dashed #CBD5E1",
  borderRadius: 12,
  padding: 28,
  color: "#64748B",
  textAlign: "center",
};

const miniBadge: React.CSSProperties = {
  padding: "1px 6px",
  borderRadius: 5,
  background: "#EEF2FF",
  color: "#4F46E5",
  fontSize: 10.5,
  fontWeight: 800,
};

const tabButtonStyle: React.CSSProperties = {
  minHeight: 32,
  borderWidth: 1,
  borderStyle: "solid",
  borderColor: "#CBD5E1",
  borderRadius: 8,
  background: "#fff",
  color: "#334155",
  fontSize: 12,
  fontWeight: 900,
  cursor: "pointer",
};

const activeTabButtonStyle: React.CSSProperties = {
  ...tabButtonStyle,
  borderColor: "#2563EB",
  background: "#EFF6FF",
  color: "#1D4ED8",
};

function statusBadge(status: string): React.CSSProperties {
  const isInbound = status.includes("응답");
  const isPending = status.includes("승인");
  return {
    display: "inline-flex",
    padding: "2px 8px",
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 800,
    background: isInbound ? "#ECFDF5" : isPending ? "#FFF7ED" : "#F8FAFC",
    color: isInbound ? "#047857" : isPending ? "#C2410C" : "#475569",
  };
}

const noticeStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderRadius: 10,
  background: "#F8FAFC",
  border: "1px solid #E5EAF3",
  color: "#334155",
  fontSize: 12.5,
};

const expertComposerStyle: React.CSSProperties = {
  display: "grid",
  gap: 10,
  borderTopWidth: 1,
  borderTopStyle: "solid",
  borderTopColor: "#E2E8F0",
  padding: 14,
  background: "#fff",
};

const expertComposerRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "auto minmax(0, 1fr) 92px",
  gap: 10,
  alignItems: "end",
};

const expertMessageTextareaStyle: React.CSSProperties = {
  width: "100%",
  minWidth: 0,
  minHeight: 48,
  maxHeight: 130,
  borderWidth: 1,
  borderStyle: "solid",
  borderColor: "#D8E0EC",
  borderRadius: 10,
  padding: "11px 12px",
  font: "inherit",
  fontSize: 13.5,
  lineHeight: 1.55,
  resize: "vertical",
};

function expertSendButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    width: 92,
    minHeight: 48,
    borderWidth: 1,
    borderStyle: "solid",
    borderColor: disabled ? "#CBD5E1" : "#2563EB",
    borderRadius: 10,
    background: disabled ? "#F1F5F9" : "#2563EB",
    color: disabled ? "#94A3B8" : "#fff",
    padding: "0 12px",
    fontSize: 13,
    fontWeight: 900,
    cursor: disabled ? "not-allowed" : "pointer",
    whiteSpace: "nowrap",
  };
}

const attachButtonStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 6,
  minHeight: 42,
  borderWidth: 1,
  borderStyle: "solid",
  borderColor: "#CBD5E1",
  borderRadius: 9,
  background: "#fff",
  color: "#334155",
  padding: "0 12px",
  fontSize: 13,
  fontWeight: 900,
  cursor: "pointer",
};

const filePreviewRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 8,
  minHeight: 26,
  alignItems: "center",
};

const fileChipStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  maxWidth: "100%",
  minHeight: 26,
  borderWidth: 1,
  borderStyle: "solid",
  borderColor: "#DBEAFE",
  borderRadius: 999,
  background: "#EFF6FF",
  color: "#1D4ED8",
  padding: "0 8px",
  fontSize: 12,
  fontWeight: 800,
};

const removeFileButtonStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 18,
  height: 18,
  border: 0,
  borderRadius: 999,
  background: "#DBEAFE",
  color: "#1D4ED8",
  cursor: "pointer",
};

const langButton: React.CSSProperties = {
  padding: "7px 13px",
  borderRadius: 8,
  borderWidth: 1,
  borderStyle: "solid",
  borderColor: "#CBD5E1",
  background: "#fff",
  color: "#334155",
  fontWeight: 800,
  cursor: "pointer",
};

const activeLangButton: React.CSSProperties = {
  ...langButton,
  borderColor: "#2563EB",
  background: "#2563EB",
  color: "#fff",
};

const composerTextareaStyle: React.CSSProperties = {
  minHeight: 88,
  border: "1px solid #D8E0EC",
  borderRadius: 10,
  padding: 10,
  fontFamily: "inherit",
  fontSize: 13,
  fontWeight: 500,
  lineHeight: 1.6,
  resize: "vertical",
};

const handoffBubbleStyle: React.CSSProperties = {
  width: "min(720px, 88%)",
  border: "1px solid #FDBA74",
  borderRadius: 14,
  background: "#FFF7ED",
  color: "#0F172A",
  padding: 18,
};
