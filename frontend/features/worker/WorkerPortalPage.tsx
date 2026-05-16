"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { CalendarDays, FileText, FileUp, LogOut, MessageSquare, ShieldCheck, Upload, UserRound } from "lucide-react";

import { clearOperatorContext, getOperatorContext, type OperatorContext } from "../../lib/operatorContext";
import styles from "../pc/PcShell.module.css";

const DEFAULT_COMPANY_ID = "550e8400-e29b-41d4-a716-446655440001";

type WorkerOption = {
  id: string;
  name: string;
  full_name?: string;
  nationality?: string;
  language_label: string;
  email?: string;
  visa_type?: string;
};

type ContactMessage = {
  id: string;
  direction: "OUTBOUND" | "INBOUND";
  source?: string;
  body_original: string;
  body_ko: string;
  status: string;
  attachments?: ContactAttachment[];
  created_at?: string;
};

type ContactAttachment = {
  id: string;
  filename: string;
  mime_type?: string;
  size?: string;
};

type ContactThread = {
  id: string;
  channel?: string;
  title: string;
  worker: WorkerOption;
  messages?: ContactMessage[];
};

type DocumentRequest = {
  id: string;
  worker_id: string;
  doc_type: string;
  label: string;
  due_date: string;
  status: string;
  file_path?: string | null;
  submitted_at?: string | null;
};

export function WorkerPortalPage() {
  const router = useRouter();
  const [operator, setOperator] = useState<OperatorContext | null>(null);
  const [worker, setWorker] = useState<WorkerOption | null>(null);
  const [threads, setThreads] = useState<ContactThread[]>([]);
  const [documentRequests, setDocumentRequests] = useState<DocumentRequest[]>([]);
  const [activeTab, setActiveTab] = useState<"documents" | "messages" | "schedule">("documents");
  const [languageView, setLanguageView] = useState<"worker" | "ko">("worker");
  const [uploadingDocType, setUploadingDocType] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");

  useEffect(() => {
    const context = getOperatorContext();
    if (context.role !== "worker") {
      router.replace("/login?from=/worker");
      return;
    }
    if (context.mustChangePassword) {
      router.replace("/change-password");
      return;
    }
    setOperator(context);
    void loadWorker(context.companyId || DEFAULT_COMPANY_ID, context.workerId || "");
  }, [router]);

  async function loadWorker(companyId: string, workerId: string) {
    try {
      const [workerResponse, threadResponse, documentResponse] = await Promise.all([
        fetch(`/api/v1/contact/workers?company_id=${encodeURIComponent(companyId)}`, { cache: "no-store" }),
        fetch(`/api/v1/contact/threads?company_id=${encodeURIComponent(companyId)}&channel=portal`, { cache: "no-store" }),
        fetch(`/api/v1/documents/worker-requests?company_id=${encodeURIComponent(companyId)}&worker_id=${encodeURIComponent(workerId)}`, { cache: "no-store" }),
      ]);
      if (!workerResponse.ok || !threadResponse.ok || !documentResponse.ok) return;
      const workerData = await workerResponse.json();
      const threadData = await threadResponse.json();
      const documentData = await documentResponse.json();
      const foundWorker = (workerData.workers ?? []).find((item: WorkerOption) => item.id === workerId) ?? null;
      const workerThreads = (threadData.threads ?? []).filter((thread: ContactThread) => (
        thread.worker.id === workerId && (thread.channel ?? "portal") === "portal"
      ));
      const detailedThreads = await Promise.all(
        workerThreads.map(async (thread: ContactThread) => {
          const response = await fetch(`/api/v1/contact/threads/${thread.id}`, { cache: "no-store" });
          if (!response.ok) return thread;
          const detail = await response.json() as ContactThread;
          return {
            ...detail,
            messages: (detail.messages ?? []).filter((message) => isWorkerVisibleMessage(message)),
          };
        }),
      );
      setWorker(foundWorker);
      setThreads(detailedThreads);
      setDocumentRequests(documentData.requests ?? []);
    } catch {
      setThreads([]);
    }
  }

  const messages = useMemo(
    () => threads.flatMap((thread) => (thread.messages ?? []).filter((message) => isWorkerVisibleMessage(message))),
    [threads],
  );

  function logout() {
    clearOperatorContext();
    router.push("/login");
  }

  async function uploadDocument(docType: string, file: File | null) {
    if (!file || !operator?.workerId) return;
    setUploadingDocType(docType);
    setUploadMessage("");
    try {
      const formData = new FormData();
      formData.append("worker_id", operator.workerId);
      formData.append("company_id", operator.companyId || DEFAULT_COMPANY_ID);
      formData.append("doc_type", docType);
      formData.append("file", file);
      const response = await fetch("/api/v1/documents/worker-submissions", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        setUploadMessage("업로드에 실패했습니다. 다시 시도해주세요.");
        return;
      }
      setUploadMessage("파일이 제출됐습니다. 담당자 확인 전까지 완료 처리되지 않습니다.");
      await loadWorker(operator.companyId || DEFAULT_COMPANY_ID, operator.workerId);
    } finally {
      setUploadingDocType("");
    }
  }

  const displayName = operator?.displayName || worker?.name || "근로자";

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.topbar}>
          <div className={styles.leftCluster}>
            <Link className={styles.brand} href="/worker" aria-label="외고반장 근로자 포털">
              <span className={styles.brandMark}>반</span>
              <span className={styles.brandName}>외고반장</span>
            </Link>
            <span className={styles.divider} aria-hidden />
            <button className={styles.company} type="button">
              <span className={styles.companyMark}>근</span>
              근로자 포털
            </button>
          </div>

          <div className={styles.rightCluster}>
            <div className={styles.person}>
              <span className={styles.avatar}>{displayName.slice(0, 1)}</span>
              <span>
                <span className={styles.manager}>{displayName}</span>
                <span className={styles.role}>근로자</span>
              </span>
            </div>
            <button className={styles.loginButton} onClick={logout} type="button">
              <LogOut size={14} /> 로그아웃
            </button>
          </div>
        </div>

        <nav className={styles.nav} aria-label="근로자 주요 메뉴">
          <button
            className={`${styles.navItem} ${activeTab === "documents" ? styles.navItemActive : ""}`}
            onClick={() => setActiveTab("documents")}
            type="button"
          >
            <FileUp size={16} /> 요청 서류
          </button>
          <button
            className={`${styles.navItem} ${activeTab === "messages" ? styles.navItemActive : ""}`}
            onClick={() => setActiveTab("messages")}
            type="button"
          >
            <MessageSquare size={16} /> 메시지
          </button>
          <button
            className={`${styles.navItem} ${activeTab === "schedule" ? styles.navItemActive : ""}`}
            onClick={() => setActiveTab("schedule")}
            type="button"
          >
            <CalendarDays size={16} /> 내 일정
          </button>
        </nav>
      </header>

      <main className={styles.main}>
        <div className={styles.stack}>
          <section className={styles.card} style={{ padding: 22 }}>
            <div className={styles.sectionTitle}>
              <div>
                <div className={styles.subtle}>근로자 홈</div>
                <h1 className={styles.headline} style={{ marginBottom: 8 }}>{worker?.name ?? "근로자"}</h1>
                {worker ? (
                  <p className={styles.subtle} style={{ margin: 0 }}>
                    {[worker.nationality, worker.visa_type, worker.email].filter(Boolean).join(" · ")}
                  </p>
                ) : null}
              </div>
              <span className={styles.workerAvatar}>
                <UserRound size={24} />
              </span>
            </div>
          </section>

          {activeTab === "documents" ? (
            <section className={styles.card} style={{ padding: 20 }}>
              <div className={styles.sectionTitle}>
                <h2 style={{ margin: 0, fontSize: 18 }}>요청 서류</h2>
                <FileUp size={18} color="#2563EB" />
              </div>
              <div style={{ display: "grid", gap: 10 }}>
                {documentRequests.map((item) => (
                  <div style={rowStyle} key={item.label}>
                    <div>
                      <strong>{item.label}</strong>
                      <div className={styles.subtle}>
                        마감 {item.due_date} {item.submitted_at ? `· 제출 ${item.submitted_at.slice(0, 10)}` : ""}
                      </div>
                      {item.file_path ? (
                        <a
                          href={`/api/v1/documents/worker-requests/${encodeURIComponent(item.worker_id)}/${encodeURIComponent(item.doc_type)}/download`}
                          style={submittedFileLinkStyle}
                        >
                          <FileText size={13} /> 제출한 서류 다운로드
                        </a>
                      ) : null}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={statusFor(item.status)}>{labelForStatus(item.status)}</span>
                      <label style={uploadButtonStyle}>
                        <Upload size={13} />
                        {uploadingDocType === item.doc_type ? "업로드 중" : "파일 선택"}
                        <input
                          disabled={Boolean(uploadingDocType)}
                          onChange={(event) => void uploadDocument(item.doc_type, event.target.files?.[0] ?? null)}
                          style={{ display: "none" }}
                          type="file"
                        />
                      </label>
                    </div>
                  </div>
                ))}
                {documentRequests.length === 0 ? (
                  <div style={emptyStyle}>현재 관리자에게 요청받은 서류가 없습니다.</div>
                ) : null}
              </div>
              {uploadMessage ? <p className={styles.safeNotice} style={{ marginTop: 16 }}>{uploadMessage}</p> : null}
            </section>
          ) : null}

          {activeTab === "messages" ? (
            <section className={styles.card} style={{ padding: 20 }}>
              <div className={styles.sectionTitle}>
                <h2 style={{ margin: 0, fontSize: 18 }}>회사 메시지</h2>
                <MessageSquare size={18} color="#2563EB" />
              </div>
              <div className={styles.safeNotice} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <ShieldCheck size={17} />
                제출된 자료는 담당자 확인 전까지 자동 완료 처리되지 않습니다.
              </div>
              {messages.length > 0 ? (
                <>
                  <div className={styles.buttonRow} style={{ marginBottom: 12 }}>
                    <button
                      style={languageView === "worker" ? activeFilterStyle : filterStyle}
                      onClick={() => setLanguageView("worker")}
                      type="button"
                    >
                      {worker?.language_label ?? "원문"}
                    </button>
                    <button
                      style={languageView === "ko" ? activeFilterStyle : filterStyle}
                      onClick={() => setLanguageView("ko")}
                      type="button"
                    >
                      한국어
                    </button>
                  </div>
                  <div style={{ display: "grid", gap: 12 }}>
                    {messages.map((message) => (
                      <WorkerMessageBubble
                        key={message.id}
                        languageView={languageView}
                        message={message}
                        workerLanguageLabel={worker?.language_label ?? "원문"}
                      />
                    ))}
                  </div>
                </>
              ) : (
                <div style={emptyStyle}>아직 도착한 메시지가 없습니다.</div>
              )}
            </section>
          ) : null}

          {activeTab === "schedule" ? (
          <section className={styles.card} style={{ padding: 20 }}>
            <div className={styles.sectionTitle}>
              <h2 style={{ margin: 0, fontSize: 18 }}>내 일정</h2>
              <CalendarDays size={18} color="#2563EB" />
            </div>
            <div style={rowStyle}>
              <div>
                <strong>서류 제출 마감</strong>
                <div className={styles.subtle}>담당자가 요청한 서류 기준</div>
              </div>
              <span style={{ ...statusStyle, color: "#1D4ED8", background: "#EFF6FF" }}>
                {documentRequests[0]?.due_date ?? "2026-05-20"}
              </span>
            </div>
          </section>
          ) : null}
        </div>
      </main>
    </div>
  );
}

function WorkerMessageBubble({
  message,
  languageView,
  workerLanguageLabel,
}: {
  message: ContactMessage;
  languageView: "worker" | "ko";
  workerLanguageLabel: string;
}) {
  const inbound = message.direction === "INBOUND";
  const body = languageView === "ko" ? message.body_ko : message.body_original;
  return (
    <div style={{ display: "flex", justifyContent: inbound ? "flex-end" : "flex-start" }}>
      <div
        style={{
          width: "min(620px, 86%)",
          border: inbound ? "1px solid #A7F3D0" : "1px solid #BFDBFE",
          borderRadius: 14,
          background: inbound ? "#F0FDFA" : "#EFF6FF",
          padding: 16,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 8 }}>
          <strong style={{ fontSize: 13 }}>{inbound ? "내 제출" : "관리자 메시지"}</strong>
          <span className={styles.subtle} style={{ fontSize: 11 }}>
            {languageView === "ko" ? "한국어" : workerLanguageLabel} · {message.status}
          </span>
        </div>
        <div style={{ whiteSpace: "pre-line", lineHeight: 1.7, fontSize: 14 }}>{body}</div>
        {message.attachments && message.attachments.length > 0 ? (
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            {message.attachments.map((attachment) => (
              <div key={attachment.id} style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid #D8E0EC", borderRadius: 10, background: "#fff", padding: "9px 10px" }}>
                <FileText size={15} color="#2563EB" />
                <a
                  href={`/api/v1/documents/attachments/${encodeURIComponent(attachment.id)}/download`}
                  style={messageAttachmentLinkStyle}
                >
                  {attachment.filename}
                </a>
                <span className={styles.subtle} style={{ fontSize: 12 }}>{attachment.size}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function isWorkerVisibleMessage(message: ContactMessage) {
  return !["EXPERT_REVIEW", "EXPERT_REPLY", "MANAGER"].includes(message.source ?? "");
}

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 14,
  borderTop: "1px solid #F1F5F9",
  padding: "13px 0",
};

const statusStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: 999,
  background: "#FFF7ED",
  color: "#C2410C",
  padding: "5px 10px",
  fontSize: 12,
  fontWeight: 900,
  whiteSpace: "nowrap",
};

const filterStyle: React.CSSProperties = {
  minHeight: 36,
  border: "1px solid #D8E0EC",
  borderRadius: 10,
  background: "#fff",
  color: "#334155",
  padding: "0 12px",
  fontSize: 13,
  fontWeight: 900,
  cursor: "pointer",
};

const activeFilterStyle: React.CSSProperties = {
  ...filterStyle,
  border: "1px solid #2563EB",
  background: "#2563EB",
  color: "#fff",
};

const emptyStyle: React.CSSProperties = {
  border: "1px dashed #CBD5E1",
  borderRadius: 12,
  color: "#64748B",
  padding: 22,
  textAlign: "center",
};

const uploadButtonStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  minHeight: 32,
  border: "1px solid #D8E0EC",
  borderRadius: 9,
  background: "#fff",
  color: "#334155",
  padding: "0 10px",
  fontSize: 12,
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const submittedFileLinkStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  marginTop: 7,
  color: "#1D4ED8",
  fontSize: 12.5,
  fontWeight: 900,
  textDecoration: "underline",
  textUnderlineOffset: 2,
};

const messageAttachmentLinkStyle: React.CSSProperties = {
  color: "#1D4ED8",
  fontSize: 13,
  fontWeight: 900,
  textDecoration: "underline",
  textUnderlineOffset: 2,
};

function statusFor(status: string): React.CSSProperties {
  if (status === "SUBMITTED") {
    return { ...statusStyle, color: "#1D4ED8", background: "#EFF6FF" };
  }
  if (status === "ACCEPTED") {
    return { ...statusStyle, color: "#047857", background: "#ECFDF5" };
  }
  return statusStyle;
}

function labelForStatus(status: string) {
  return {
    REQUESTED: "요청됨",
    SUBMITTED: "제출됨",
    ACCEPTED: "확인됨",
    REJECTED: "보완 필요",
    MISSING: "미제출",
  }[status] ?? status;
}
