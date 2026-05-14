import { FileText, MessageSquare, MessageSquarePlus } from "lucide-react";
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
};

type ContactMessage = {
  id: string;
  worker_id: string;
  direction: "OUTBOUND" | "INBOUND";
  source: "LANGCHAIN" | "PORTAL" | string;
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
  worker: WorkerOption;
  title: string;
  status: string;
  last_message_at?: string;
  last_message_preview?: string;
  message_count: number;
  messages?: ContactMessage[];
};

export function ContactView({ onAction }: PcViewProps = {}) {
  const searchParams = useSearchParams();
  const [workers, setWorkers] = useState<WorkerOption[]>([]);
  const [threads, setThreads] = useState<ContactThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<ContactThread | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState("");
  const [languageView, setLanguageView] = useState<"worker" | "ko">("worker");
  const [composerOpen, setComposerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const requestedWorkerId = searchParams.get("worker_id");
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
    if (!requestedWorkerId || threads.length === 0) return;
    const found = threads.find((thread) => thread.worker.id === requestedWorkerId);
    if (found) {
      void selectThread(found.id);
    }
  }, [requestedWorkerId, threads]);

  async function loadInitial() {
    setLoading(true);
    try {
      const [workerResponse, threadResponse] = await Promise.all([
        fetch(`/api/v1/contact/workers?company_id=${encodeURIComponent(COMPANY_ID)}`, { cache: "no-store" }),
        fetch(`/api/v1/contact/threads?company_id=${encodeURIComponent(COMPANY_ID)}`, { cache: "no-store" }),
      ]);
      const workerData = await workerResponse.json();
      const threadData = await threadResponse.json();
      const nextWorkers = workerData.workers ?? [];
      const nextThreads = threadData.threads ?? [];
      setWorkers(nextWorkers);
      setThreads(nextThreads);
      setSelectedWorkerId(requestedWorkerId || nextWorkers[0]?.id || "");
      if (nextThreads.length > 0) {
        await selectThread(nextThreads[0].id);
      } else {
        setSelectedThread(null);
      }
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
  }

  async function refreshSelectedThread(threadId: string) {
    const response = await fetch(`/api/v1/contact/threads/${threadId}`, { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    setSelectedThread(data);
    setSelectedWorkerId(data.worker?.id ?? "");
  }

  async function createDraft() {
    if (!selectedWorkerId) return;
    setWorking(true);
    try {
      const response = await fetch("/api/v1/contact/messages/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          worker_id: selectedWorkerId,
          company_id: COMPANY_ID,
          due_date: "2026-05-20",
          user_id: "user-demo-001",
        }),
      });
      if (response.ok) {
        const thread = await response.json();
        setComposerOpen(false);
        await loadInitial();
        await selectThread(thread.id);
      }
    } finally {
      setWorking(false);
    }
  }

  const detailWorker = selectedThread?.worker;
  const messages = selectedThread?.messages ?? [];
  const workerLanguageLabel = detailWorker?.language_label ?? selectedWorker?.language_label ?? "원문";

  return (
    <div className={styles.stack}>
      <div className={styles.pageHead}>
        <div>
          <div className={styles.subtle}>메시지 관리</div>
          <h1 className={styles.headline}>메시지 관리</h1>
          <p className={styles.subtle}>근로자별 다국어 메시지 초안과 포털 응답을 한 곳에서 확인합니다.</p>
        </div>
        <div className={styles.buttonRow}>
          <Button disabled={working || workers.length === 0} onClick={() => setComposerOpen(true)}>
            <MessageSquarePlus size={15} /> 메시지 생성
          </Button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px minmax(0, 1fr)", gap: 18, alignItems: "start" }}>
        <aside className={styles.contactList}>
          <div style={{ padding: "12px 14px", borderBottom: "1px solid #E5EAF3" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B" }}>
              메시지 목록 · {threads.length}건
            </div>
          </div>

          {loading ? (
            <div style={emptyStyle}>불러오는 중입니다.</div>
          ) : threads.length === 0 ? (
            <div style={emptyStyle}>메시지가 없습니다.</div>
          ) : (
            threads.map((thread) => {
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
                      <strong style={{ fontSize: 13.5 }}>{thread.worker.name}</strong>
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

        <section className={styles.document} style={{ minHeight: 620 }}>
          {requestedActionLabel ? (
            <div style={{ ...noticeStyle, marginBottom: 14 }}>
              오늘 할 일에서 이동: {detailWorker?.name ?? selectedWorker?.name ?? "근로자"} · {requestedActionLabel}
            </div>
          ) : null}

          {selectedThread ? (
            <>
              <div className={styles.pageHead} style={{ marginBottom: 16 }}>
                <div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                    <MessageSquare size={17} color="#2563EB" />
                    <h2 style={{ margin: 0, fontSize: 19 }}>{detailWorker?.name ?? "근로자"}</h2>
                  </div>
                  <p className={styles.subtle} style={{ margin: 0 }}>
                    {detailWorker?.nationality ?? "-"} · {detailWorker?.visa_type ?? "-"} · {detailWorker?.email ?? "이메일 없음"}
                  </p>
                </div>
                <div className={styles.buttonRow}>
                  <button
                    type="button"
                    onClick={() => setLanguageView("worker")}
                    style={languageView === "worker" ? activeLangButton : langButton}
                  >
                    {workerLanguageLabel}
                  </button>
                  <button
                    type="button"
                    onClick={() => setLanguageView("ko")}
                    style={languageView === "ko" ? activeLangButton : langButton}
                  >
                    한국어
                  </button>
                </div>
              </div>

              <div style={noticeStyle}>
                근로자 포털 응답은 본인 계정과 매칭해 표시합니다. 실제 외부 발송은 담당자 승인 전에는 수행하지 않습니다.
              </div>

              <div style={{ display: "grid", gap: 14, marginTop: 18 }}>
                {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  languageView={languageView}
                  message={message}
                  onAccepted={() => void refreshSelectedThread(selectedThread.id)}
                  workerLanguageLabel={workerLanguageLabel}
                />
                ))}
              </div>
            </>
          ) : (
            <div style={emptyDetailStyle}>
              <MessageSquare size={28} color="#94A3B8" />
              <strong style={{ display: "block", marginTop: 10, color: "#334155" }}>메시지가 없습니다.</strong>
              <div style={{ marginTop: 6 }}>메시지를 생성하거나 메일을 확인하면 대화 내용이 여기에 표시됩니다.</div>
            </div>
          )}
        </section>
      </div>

      {composerOpen ? (
        <div style={overlayStyle}>
          <div style={composerStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
              <div>
                <div className={styles.subtle} style={{ fontSize: 12 }}>LangChain 다국어 초안</div>
                <h2 style={{ margin: "4px 0 0", fontSize: 20 }}>메시지 생성</h2>
              </div>
              <button
                aria-label="닫기"
                onClick={() => setComposerOpen(false)}
                style={closeButtonStyle}
                type="button"
              >
                ×
              </button>
            </div>

            <label style={fieldLabelStyle}>
              근로자
              <select
                value={selectedWorkerId}
                onChange={(event) => setSelectedWorkerId(event.target.value)}
                style={selectStyle}
              >
                {workers.map((worker) => (
                  <option key={worker.id} value={worker.id}>{worker.name} · {worker.language_label}</option>
                ))}
              </select>
            </label>

            <div style={noticeStyle}>
              선택한 근로자의 요청 서류 상태를 기준으로 LangChain이 메시지 초안을 생성합니다.
              실제 발송은 별도 승인 전에는 수행하지 않습니다.
            </div>

            <div className={styles.buttonRow} style={{ justifyContent: "flex-end" }}>
              <Button disabled={working} variant="secondary" onClick={() => setComposerOpen(false)}>
                취소
              </Button>
              <Button disabled={working || !selectedWorkerId} onClick={createDraft}>
                <MessageSquarePlus size={15} /> 초안 생성
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MessageBubble({
  message,
  languageView,
  onAccepted,
  workerLanguageLabel,
}: {
  message: ContactMessage;
  languageView: "worker" | "ko";
  onAccepted: () => void;
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
      setReviewMessage("서류가 승인 처리됐습니다.");
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
      window.setTimeout(onAccepted, 600);
      return;
    }
    const error = await response.json().catch(() => null);
    setReviewMessage(error?.detail || "보완 요청 처리에 실패했습니다.");
  }
  return (
    <div style={{ display: "flex", justifyContent: outbound ? "flex-end" : "flex-start" }}>
      <div
        style={{
          width: "min(680px, 82%)",
          border: outbound ? "1px solid #BFDBFE" : "1px solid #A7F3D0",
          borderRadius: 14,
          background: outbound ? "#EFF6FF" : "#F0FDFA",
          padding: 18,
          color: "#0F172A",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
          <strong style={{ fontSize: 13 }}>{outbound ? "AI 초안" : "근로자 포털 응답"}</strong>
          <span className={styles.subtle} style={{ fontSize: 11 }}>
            {languageView === "ko" ? "한국어" : workerLanguageLabel} · {message.status}
          </span>
        </div>
        <div style={{ whiteSpace: "pre-line", lineHeight: 1.75, fontSize: 14.5 }}>{body}</div>
        {message.attachments.length > 0 ? (
          <div style={{ display: "grid", gap: 8, marginTop: 14 }}>
            {message.attachments.map((attachment) => (
              <div key={attachment.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 10px", borderRadius: 10, background: "#fff", border: "1px solid #E5EAF3" }}>
                <FileText size={15} color="#2563EB" />
                <a
                  href={`/api/v1/documents/attachments/${encodeURIComponent(attachment.id)}/download`}
                  style={attachmentLinkStyle}
                >
                  {attachment.filename}
                </a>
                <span className={styles.subtle} style={{ fontSize: 12 }}>{attachment.size}</span>
                {!outbound && attachment.doc_type ? (
                  <div style={documentReviewActionsStyle}>
                    <button
                      onClick={() => void acceptDocument(attachment.doc_type || "")}
                      style={confirmDocumentButtonStyle}
                      type="button"
                    >
                      승인
                    </button>
                    <button
                      onClick={() => void rejectDocument(attachment.doc_type || "")}
                      style={rejectDocumentButtonStyle}
                      type="button"
                    >
                      보완 요청
                    </button>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
        {reviewMessage ? (
          <div style={documentReviewNoticeStyle}>{reviewMessage}</div>
        ) : null}
      </div>
    </div>
  );
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

const selectStyle: React.CSSProperties = {
  width: "100%",
  height: 36,
  border: "1px solid #E5EAF3",
  borderRadius: 8,
  padding: "0 10px",
  fontSize: 12.5,
  background: "#fff",
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
