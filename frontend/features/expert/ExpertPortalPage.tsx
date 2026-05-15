"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ClipboardCheck, LogOut, MessageSquare, Pencil, Send, ShieldCheck } from "lucide-react";

import { clearOperatorContext, getOperatorContext, type OperatorContext } from "../../lib/operatorContext";
import styles from "../pc/PcShell.module.css";

const COMPANY_ID = "550e8400-e29b-41d4-a716-446655440001";

type ExpertStatus = "검토 대기" | "의견 작성 중" | "검토 완료";

type ContactMessage = {
  id: string;
  direction: "OUTBOUND" | "INBOUND";
  source: "EXPERT_REVIEW" | "EXPERT_REPLY" | "MANAGER" | string;
  body_ko: string;
  body_original: string;
  status: string;
  created_at?: string;
};

type ContactThread = {
  id: string;
  channel?: string;
  worker: {
    id: string;
    name: string;
    nationality?: string;
    visa_type?: string;
  };
  title: string;
  status: string;
  last_message_preview?: string;
  message_count: number;
  messages?: ContactMessage[];
};

export function ExpertPortalPage() {
  const router = useRouter();
  const [operator, setOperator] = useState<OperatorContext | null>(null);
  const [activeTab, setActiveTab] = useState<"requests" | "messages">("requests");
  const [threads, setThreads] = useState<ContactThread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState("");
  const [draftMessage, setDraftMessage] = useState("");
  const [revisionTarget, setRevisionTarget] = useState<ContactMessage | null>(null);
  const [revisionDraft, setRevisionDraft] = useState("");
  const [editingMessage, setEditingMessage] = useState<ContactMessage | null>(null);
  const [editDraft, setEditDraft] = useState("");

  useEffect(() => {
    const context = getOperatorContext();
    if (context.role !== "expert") {
      router.replace("/login?from=/expert");
      return;
    }
    setOperator(context);
    void refreshInbox();
  }, [router]);

  useEffect(() => {
    if (!selectedThreadId) return;
    const timer = window.setInterval(() => {
      void refreshThread(selectedThreadId);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [selectedThreadId]);

  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === selectedThreadId) ?? threads[0],
    [threads, selectedThreadId],
  );
  const requests = useMemo(() => threads.map(threadToRequest), [threads]);
  const selectedRequest = useMemo(
    () => requests.find((request) => request.id === selectedThreadId) ?? requests[0],
    [requests, selectedThreadId],
  );

  async function refreshInbox() {
    const response = await fetch(`/api/v1/contact/threads?company_id=${encodeURIComponent(COMPANY_ID)}&channel=expert`, { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    const nextThreads = data.threads ?? [];
    const nextSelectedId = nextThreads.some((thread: ContactThread) => thread.id === selectedThreadId) ? selectedThreadId : nextThreads[0]?.id || "";
    setThreads(nextThreads);
    setSelectedThreadId(nextSelectedId);
    if (nextSelectedId) await refreshThread(nextSelectedId);
  }

  async function refreshThread(threadId: string) {
    const response = await fetch(`/api/v1/contact/threads/${encodeURIComponent(threadId)}`, { cache: "no-store" });
    if (!response.ok) return;
    const thread = await response.json() as ContactThread;
    setThreads((items) => items.map((item) => item.id === thread.id ? thread : item));
  }

  async function selectThread(threadId: string) {
    setSelectedThreadId(threadId);
    await refreshThread(threadId);
  }

  function logout() {
    clearOperatorContext();
    router.push("/login");
  }

  async function sendExpertMessage(body: string, status = "행정사 답변") {
    if (!selectedThread) return;
    const text = body.trim();
    if (!text) return;
    const response = await fetch(`/api/v1/contact/threads/${encodeURIComponent(selectedThread.id)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        body_ko: text,
        body_original: text,
        language_code: "ko",
        source: "EXPERT_REPLY",
        status,
        direction: "INBOUND",
      }),
    });
    if (!response.ok) return;
    const savedThread = await response.json() as ContactThread;
    setThreads((items) => items.map((thread) => thread.id === savedThread.id ? savedThread : thread));
    setSelectedThreadId(savedThread.id);
    setDraftMessage("");
  }

  function approveManagerRequest(message: ContactMessage) {
    void sendExpertMessage(buildApprovalDraft(message.body_ko), "행정사 승인");
  }

  function openRevisionRequest(message: ContactMessage) {
    setRevisionTarget(message);
    setRevisionDraft(buildRevisionDraft(message.body_ko));
  }

  async function submitRevisionRequest() {
    if (!revisionTarget) return;
    await sendExpertMessage(revisionDraft, "행정사 보완 요청");
    setRevisionTarget(null);
    setRevisionDraft("");
  }

  function openMessageEdit(message: ContactMessage) {
    setEditingMessage(message);
    setEditDraft(message.body_ko);
  }

  async function submitMessageEdit() {
    if (!editingMessage) return;
    const body = editDraft.trim();
    if (!body) return;
    const response = await fetch(`/api/v1/contact/messages/${encodeURIComponent(editingMessage.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body_ko: body, body_original: body }),
    });
    if (!response.ok) return;
    const savedThread = await response.json() as ContactThread;
    setThreads((items) => items.map((thread) => thread.id === savedThread.id ? savedThread : thread));
    setEditingMessage(null);
    setEditDraft("");
  }

  if (!operator) return <div className={styles.shell} />;

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.topbar}>
          <div className={styles.leftCluster}>
            <Link className={styles.brand} href="/expert" aria-label="외고반장 행정사 포털">
              <span className={styles.brandMark}>반</span>
              <span className={styles.brandName}>외고반장</span>
            </Link>
            <span className={styles.divider} aria-hidden />
            <button className={styles.company} type="button"><span className={styles.companyMark}>행</span>행정사 포털</button>
          </div>
          <div className={styles.rightCluster}>
            <div className={styles.person}>
              <span className={styles.avatar}>{(operator.displayName || "행").slice(0, 1)}</span>
              <span>
                <span className={styles.manager}>{operator.displayName || "행정사"}</span>
                <span className={styles.role}>외부 검토자</span>
              </span>
            </div>
            <button className={styles.loginButton} onClick={logout} type="button"><LogOut size={14} /> 로그아웃</button>
          </div>
        </div>
        <nav className={styles.nav} aria-label="행정사 주요 메뉴">
          <button className={`${styles.navItem} ${activeTab === "requests" ? styles.navItemActive : ""}`} onClick={() => setActiveTab("requests")} type="button">
            <ClipboardCheck size={16} /> 요청 목록
          </button>
          <button className={`${styles.navItem} ${activeTab === "messages" ? styles.navItemActive : ""}`} onClick={() => setActiveTab("messages")} type="button">
            <MessageSquare size={16} /> 메시지 관리
          </button>
        </nav>
      </header>

      <main className={styles.main}>
        {activeTab === "requests" ? (
          <div className={styles.split}>
            <aside className={styles.sideStack}>
              <section className={styles.card} style={{ padding: 16 }}>
                <div className={styles.sectionTitle}>
                  <h1 style={{ margin: 0, fontSize: 18 }}>검토 요청</h1>
                  <span className={styles.badge}>{requests.length}건</span>
                </div>
                {requests.length === 0 ? (
                  <EmptyState title="도착한 검토 요청이 없습니다" description="관리자가 행정사 검토 요청을 보내면 근로자별 요청이 표시됩니다." />
                ) : (
                  <div style={{ display: "grid", gap: 10 }}>
                    {requests.map((request) => (
                      <button key={request.id} onClick={() => void selectThread(request.id)} style={requestCardStyle(selectedThreadId === request.id)} type="button">
                        <strong style={{ display: "block", fontSize: 14 }}>{request.title}</strong>
                        <span className={styles.subtle} style={{ display: "block", marginTop: 5, fontSize: 12 }}>{request.worker} · {request.due}</span>
                        <span style={statusChip(request.status)}>{request.status}</span>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            </aside>

            {selectedRequest ? (
              <section className={styles.document}>
                <div className={styles.pageHead}>
                  <div>
                    <div className={styles.subtle}>{selectedRequest.id}</div>
                    <h1 className={styles.headline}>{selectedRequest.title}</h1>
                    <p className={styles.subtle}>{selectedRequest.company} · {selectedRequest.worker}</p>
                  </div>
                  <span style={statusChip(selectedRequest.status)}>{selectedRequest.status}</span>
                </div>
                <div className={styles.safeNotice} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 18 }}>
                  <ShieldCheck size={17} /> 검토 의견은 담당자 확인용입니다. 정부 제출이나 대외 발송은 이 화면에서 실행하지 않습니다.
                </div>
                <section style={{ marginBottom: 22 }}>
                  <h2 style={{ fontSize: 17 }}>요청 요약</h2>
                  <p style={{ lineHeight: 1.8, whiteSpace: "pre-line" }}>{selectedRequest.summary}</p>
                </section>
                <div className={styles.infoGrid} style={{ marginBottom: 22 }}>
                  <InfoBlock title="전달 자료" items={["관리자 검토 요청 본문", "근로자 기본 정보", "제출 서류 상태"]} />
                  <InfoBlock title="검토 기준" items={["가능 여부 확정 금지", "추가 서류와 리스크 중심", "담당자 승인 후 후속 진행"]} />
                </div>
                <button className={styles.primaryWideButton} onClick={() => setActiveTab("messages")} style={{ width: "auto", padding: "0 16px" }} type="button">
                  메시지에서 답변하기
                </button>
              </section>
            ) : (
              <section className={styles.document}>
                <EmptyState title="선택할 요청이 없습니다" description="관리자가 실제 케이스를 검토 요청하면 요약과 메시지가 여기에 열립니다." />
              </section>
            )}
          </div>
        ) : (
          <section className={styles.card} style={{ overflow: "hidden" }}>
            <div className={styles.contactLayout}>
              <aside className={styles.contactList}>
                <div style={{ padding: 14, borderBottom: "1px solid #E2E8F0" }}><strong style={{ fontSize: 13 }}>메시지 목록</strong></div>
                {threads.length === 0 ? (
                  <div style={{ padding: 14 }}><EmptyState title="메시지가 없습니다" description="관리자가 행정사 검토 요청을 보내면 근로자별 메신저가 생성됩니다." /></div>
                ) : (
                  threads.map((thread) => (
                    <button className={styles.contactItem} key={thread.id} onClick={() => void selectThread(thread.id)} style={threadButtonStyle(selectedThread?.id === thread.id)} type="button">
                      <span className={styles.workerAvatar}>{thread.worker.name.slice(0, 1)}</span>
                      <div style={{ minWidth: 0 }}>
                        <strong style={{ fontSize: 13 }}>{thread.title}</strong>
                        <div className={styles.subtle} style={{ fontSize: 12, marginTop: 5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {thread.last_message_preview || "메시지 없음"}
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </aside>

              {selectedThread ? (
                <MessengerPanel
                  messages={selectedThread.messages ?? []}
                  title={selectedThread.title}
                  draftMessage={draftMessage}
                  onDraftChange={setDraftMessage}
                  onApprove={approveManagerRequest}
                  onEdit={openMessageEdit}
                  onRevision={openRevisionRequest}
                  onSend={() => void sendExpertMessage(draftMessage)}
                />
              ) : (
                <div style={{ display: "grid", minHeight: 680, placeItems: "center", padding: 24 }}>
                  <EmptyState title="열린 대화가 없습니다" description="관리자가 보낸 검토 요청이 도착하면 이 영역에서 답변할 수 있습니다." />
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      {revisionTarget ? (
        <RevisionModal
          draft={revisionDraft}
          onClose={() => {
            setRevisionTarget(null);
            setRevisionDraft("");
          }}
          onDraftChange={setRevisionDraft}
          onSubmit={submitRevisionRequest}
          sourceBody={revisionTarget.body_ko}
        />
      ) : null}
      {editingMessage ? (
        <EditMessageModal
          draft={editDraft}
          onClose={() => {
            setEditingMessage(null);
            setEditDraft("");
          }}
          onDraftChange={setEditDraft}
          onSubmit={submitMessageEdit}
        />
      ) : null}
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div style={{ border: "1px dashed #CBD5E1", borderRadius: 12, padding: 18, background: "#F8FAFC" }}>
      <strong style={{ display: "block", fontSize: 14, color: "#0F172A" }}>{title}</strong>
      <p className={styles.subtle} style={{ margin: "8px 0 0", lineHeight: 1.6 }}>{description}</p>
    </div>
  );
}

function MessengerPanel({
  messages,
  title,
  draftMessage,
  onDraftChange,
  onApprove,
  onEdit,
  onRevision,
  onSend,
}: {
  messages: ContactMessage[];
  title: string;
  draftMessage: string;
  onDraftChange: (value: string) => void;
  onApprove: (message: ContactMessage) => void;
  onEdit: (message: ContactMessage) => void;
  onRevision: (message: ContactMessage) => void;
  onSend: () => void;
}) {
  return (
    <div style={{ display: "grid", gridTemplateRows: "auto minmax(0, 1fr) auto", minHeight: 680 }}>
      <div style={{ padding: 20, borderBottom: "1px solid #E2E8F0" }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>{title}</h1>
        <p className={styles.subtle} style={{ margin: "6px 0 0" }}>검토 요청과 관련된 담당자-행정사 대화입니다.</p>
      </div>

      <div style={{ display: "grid", alignContent: "end", gap: 12, padding: 20, background: "#F8FAFC" }}>
        {messages.map((message, index) => {
          const expert = isExpertMessage(message);
          return (
            <div key={message.id} style={{ display: "flex", justifyContent: expert ? "flex-end" : "flex-start" }}>
              <div style={expert ? expertBubbleStyle : managerBubbleStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 6 }}>
                  <strong style={{ display: "block", fontSize: 12 }}>{expert ? "행정사" : "담당자"} · {formatTime(message.created_at)}</strong>
                  {canEditExpertMessage(messages, message, index) ? (
                    <button onClick={() => onEdit(message)} style={editMessageButtonStyle} type="button"><Pencil size={12} /> 수정</button>
                  ) : null}
                </div>
                <span style={{ whiteSpace: "pre-line", lineHeight: 1.7 }}>{message.body_ko}</span>
                {!expert && !isReviewedMessage(messages, index) ? (
                  <div className={styles.buttonRow} style={{ justifyContent: "flex-end", marginTop: 12 }}>
                    <button onClick={() => onApprove(message)} style={expertApproveButtonStyle} type="button">승인</button>
                    <button onClick={() => onRevision(message)} style={expertRevisionButtonStyle} type="button">보완 요청</button>
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSend();
        }}
        style={composerBarStyle}
      >
        <input aria-label="메시지 입력" onChange={(event) => onDraftChange(event.target.value)} placeholder="담당자에게 보낼 메시지를 입력하세요" style={messageInputStyle} value={draftMessage} />
        <button className={styles.primaryWideButton} style={{ width: 92 }} type="submit"><Send size={14} /> 전송</button>
      </form>
    </div>
  );
}

function threadToRequest(thread: ContactThread) {
  const messages = thread.messages ?? [];
  const firstManagerMessage = messages.find((message) => !isExpertMessage(message));
  const latestExpertMessage = [...messages].reverse().find((message) => isExpertMessage(message));
  const status: ExpertStatus = latestExpertMessage?.status.includes("승인")
    ? "검토 완료"
    : latestExpertMessage
      ? "의견 작성 중"
      : thread.status.includes("승인")
        ? "검토 완료"
        : thread.status.includes("행정사 보완") || thread.status.includes("행정사 답변")
          ? "의견 작성 중"
          : "검토 대기";
  return {
    id: thread.id,
    title: thread.title,
    worker: thread.worker.name,
    company: "삼성전자 부산공장",
    due: "담당자 확인 후",
    status,
    summary: firstManagerMessage?.body_ko || thread.last_message_preview || "관리자가 보낸 검토 요청입니다.",
  };
}

function isExpertMessage(message: ContactMessage) {
  return message.source === "EXPERT_REPLY" || message.direction === "INBOUND";
}

function isReviewedMessage(messages: ContactMessage[], messageIndex: number) {
  return messages.slice(messageIndex + 1).some(isExpertMessage);
}

function canEditExpertMessage(messages: ContactMessage[], target: ContactMessage, messageIndex: number) {
  if (!isExpertMessage(target)) return false;
  return !messages.slice(messageIndex + 1).some((message) => !isExpertMessage(message));
}

function formatTime(value?: string) {
  if (!value) return "";
  return new Date(value).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}

function buildApprovalDraft(sourceBody: string) {
  const expiredStay = sourceBody.includes("체류만료일") && sourceBody.includes("지난 상태");
  const passportSubmitted = sourceBody.includes("여권 사본") && sourceBody.includes("확인 완료");
  const lines = ["[LangChain 근거 재구성] 승인 의견입니다."];
  if (passportSubmitted) lines.push("근거: 요청 본문상 여권 사본은 근로자 포털 제출 및 관리자 확인 완료 상태로 정리되어 있습니다.");
  if (expiredStay) lines.push("주의: 체류만료일이 지난 케이스이므로 다음 단계 진행 전 만료 경과 사유와 실제 제출 가능 일정은 담당자가 별도 확인해야 합니다.");
  lines.push("현재 전달된 자료 기준으로 행정사 검토 단계 진행은 가능하다고 봅니다.");
  lines.push("정부 포털 제출이나 대외 발송은 이 승인 의견만으로 진행하지 않고, 담당자 최종 확인 후 별도 승인 절차를 거쳐야 합니다.");
  return lines.join("\n");
}

function buildRevisionDraft(sourceBody: string) {
  const needsArcOrContract = sourceBody.includes("외국인등록증") || sourceBody.includes("표준근로계약서") || sourceBody.includes("고용 관련 서류");
  const expiredStay = sourceBody.includes("체류만료일") && sourceBody.includes("지난 상태");
  const passportSubmitted = sourceBody.includes("여권 사본") && sourceBody.includes("확인 완료");
  const lines = ["[LangChain 근거 재구성] 보완 요청드립니다."];
  if (expiredStay) lines.push("체류만료일이 지난 케이스이므로 만료 경과 사유와 현재 진행 가능한 일정, 리스크를 먼저 확인해 주세요.");
  if (passportSubmitted) lines.push("여권 사본 제출 및 관리자 확인은 완료된 것으로 보이나, 제출본 식별 가능 여부는 원본 기준으로 다시 확인이 필요합니다.");
  if (needsArcOrContract) lines.push("요청 본문에 포함된 외국인등록증 사본, 표준근로계약서, 고용 관련 서류의 보유 여부를 추가로 확인해 주세요.");
  else lines.push("현재 요청 본문 기준으로 부족한 자료나 담당자가 추가 확인해야 할 항목을 정리해 주세요.");
  lines.push("정부 포털 제출이나 대외 발송은 진행하지 않고, 보완 자료 확인 후 다시 검토 요청드리겠습니다.");
  return lines.join("\n");
}

function RevisionModal({ draft, onClose, onDraftChange, onSubmit, sourceBody }: {
  draft: string;
  onClose: () => void;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  sourceBody: string;
}) {
  return (
    <div style={modalOverlayStyle}>
      <section aria-modal="true" role="dialog" style={modalStyle}>
        <div>
          <div className={styles.subtle} style={{ fontSize: 12 }}>근거 기반 보완 요청</div>
          <h2 style={{ margin: "4px 0 0", fontSize: 20 }}>보완 요청 메시지 작성</h2>
        </div>
        <div style={modalSourceStyle}>
          <strong style={{ display: "block", marginBottom: 8, fontSize: 12 }}>근거로 사용한 담당자 요청</strong>
          <div style={{ whiteSpace: "pre-line", lineHeight: 1.6 }}>{sourceBody}</div>
        </div>
        <label className={styles.formLabel}>행정사 보완 요청 메시지<textarea value={draft} onChange={(event) => onDraftChange(event.target.value)} style={revisionTextareaStyle} /></label>
        <div className={styles.buttonRow} style={{ justifyContent: "flex-end" }}>
          <button onClick={onClose} style={modalSecondaryButtonStyle} type="button">취소</button>
          <button disabled={!draft.trim()} onClick={onSubmit} style={modalPrimaryButtonStyle} type="button">보완 요청 전송</button>
        </div>
      </section>
    </div>
  );
}

function EditMessageModal({ draft, onClose, onDraftChange, onSubmit }: {
  draft: string;
  onClose: () => void;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <div style={modalOverlayStyle}>
      <section aria-modal="true" role="dialog" style={modalStyle}>
        <div>
          <div className={styles.subtle} style={{ fontSize: 12 }}>답변 전 메시지 수정</div>
          <h2 style={{ margin: "4px 0 0", fontSize: 20 }}>행정사 메시지 수정</h2>
        </div>
        <label className={styles.formLabel}>메시지 내용<textarea value={draft} onChange={(event) => onDraftChange(event.target.value)} style={revisionTextareaStyle} /></label>
        <div style={modalSourceStyle}>아직 담당자 답장이 붙지 않은 행정사 발신 메시지만 수정할 수 있습니다.</div>
        <div className={styles.buttonRow} style={{ justifyContent: "flex-end" }}>
          <button onClick={onClose} style={modalSecondaryButtonStyle} type="button">취소</button>
          <button disabled={!draft.trim()} onClick={onSubmit} style={modalPrimaryButtonStyle} type="button">수정 저장</button>
        </div>
      </section>
    </div>
  );
}

function InfoBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className={styles.card} style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 12px", fontSize: 15 }}>{title}</h2>
      <div style={{ display: "grid", gap: 8 }}>
        {items.map((item) => <div key={item} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}><span>{item}</span></div>)}
      </div>
    </section>
  );
}

function statusChip(status: ExpertStatus): React.CSSProperties {
  if (status === "검토 완료") return { ...baseStatusChip, background: "#ECFDF5", color: "#047857" };
  if (status === "의견 작성 중") return { ...baseStatusChip, background: "#EFF6FF", color: "#1D4ED8" };
  return { ...baseStatusChip, background: "#FFF7ED", color: "#C2410C" };
}

function requestCardStyle(selected: boolean): React.CSSProperties {
  return {
    border: selected ? "1px solid #93C5FD" : "1px solid #E2E8F0",
    borderRadius: 12,
    background: selected ? "#EFF6FF" : "#fff",
    padding: 13,
    textAlign: "left",
    cursor: "pointer",
  };
}

function threadButtonStyle(selected: boolean): React.CSSProperties {
  return {
    width: "100%",
    border: 0,
    borderLeft: selected ? "4px solid #2563EB" : "4px solid transparent",
    background: selected ? "#EFF6FF" : "transparent",
    textAlign: "left",
    cursor: "pointer",
  };
}

const baseStatusChip: React.CSSProperties = {
  display: "inline-flex",
  width: "fit-content",
  marginTop: 10,
  borderRadius: 999,
  padding: "4px 9px",
  fontSize: 12,
  fontWeight: 900,
};

const managerBubbleStyle: React.CSSProperties = {
  width: "min(620px, 82%)",
  border: "1px solid #BFDBFE",
  borderRadius: 14,
  background: "#EFF6FF",
  padding: 15,
  fontSize: 14,
};

const expertBubbleStyle: React.CSSProperties = {
  ...managerBubbleStyle,
  border: "1px solid #A7F3D0",
  background: "#ECFDF5",
};

const composerBarStyle: React.CSSProperties = {
  display: "flex",
  gap: 10,
  borderTop: "1px solid #E2E8F0",
  padding: 14,
  background: "#fff",
};

const messageInputStyle: React.CSSProperties = {
  flex: 1,
  height: 42,
  border: "1px solid #D8E0EC",
  borderRadius: 10,
  padding: "0 12px",
  font: "inherit",
  fontSize: 14,
};

const expertApproveButtonStyle: React.CSSProperties = {
  minHeight: 30,
  border: "1px solid #BBF7D0",
  borderRadius: 8,
  background: "#ECFDF5",
  color: "#047857",
  padding: "0 11px",
  fontSize: 12,
  fontWeight: 900,
  cursor: "pointer",
};

const expertRevisionButtonStyle: React.CSSProperties = {
  ...expertApproveButtonStyle,
  border: "1px solid #FED7AA",
  background: "#FFF7ED",
  color: "#C2410C",
};

const editMessageButtonStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  minHeight: 26,
  border: "1px solid #A7F3D0",
  borderRadius: 8,
  background: "#fff",
  color: "#047857",
  padding: "0 9px",
  fontSize: 12,
  fontWeight: 900,
  cursor: "pointer",
};

const modalOverlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 80,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
  background: "rgba(15, 23, 42, 0.32)",
};

const modalStyle: React.CSSProperties = {
  width: "min(760px, 100%)",
  maxHeight: "calc(100vh - 48px)",
  overflow: "auto",
  display: "grid",
  gap: 16,
  border: "1px solid #CBD5E1",
  borderRadius: 14,
  background: "#fff",
  boxShadow: "0 22px 70px rgba(15, 23, 42, 0.2)",
  padding: 22,
};

const modalSourceStyle: React.CSSProperties = {
  maxHeight: 220,
  overflow: "auto",
  border: "1px solid #E2E8F0",
  borderRadius: 10,
  background: "#F8FAFC",
  padding: 12,
  color: "#334155",
  fontSize: 12.5,
};

const revisionTextareaStyle: React.CSSProperties = {
  minHeight: 180,
  border: "1px solid #D8E0EC",
  borderRadius: 10,
  padding: 12,
  resize: "vertical",
  font: "inherit",
  fontSize: 14,
  lineHeight: 1.7,
};

const modalSecondaryButtonStyle: React.CSSProperties = {
  minHeight: 38,
  border: "1px solid #CBD5E1",
  borderRadius: 9,
  background: "#fff",
  color: "#334155",
  padding: "0 14px",
  fontSize: 13,
  fontWeight: 900,
  cursor: "pointer",
};

const modalPrimaryButtonStyle: React.CSSProperties = {
  ...modalSecondaryButtonStyle,
  border: "1px solid #FED7AA",
  background: "#FFF7ED",
  color: "#C2410C",
};
