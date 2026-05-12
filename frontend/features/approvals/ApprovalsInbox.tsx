"use client";

import { useEffect, useMemo, useState } from "react";

const COMPANY_ID = "550e8400-e29b-41d4-a716-446655440001";
const REVIEWER_ID = "manager-demo";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";
type TargetType = "contact_message" | "status_update_candidate" | "handoff_package_draft";
type TargetFilter = "all" | TargetType;

type ApprovalListItem = {
  approval_id: string;
  target_type: TargetType;
  target_id: string;
  approval_status: ApprovalStatus;
  target_status: string;
  summary: string;
  created_at: string | null;
  reviewed_at: string | null;
  target: Record<string, string | boolean | null>;
};

type ApprovalListResponse = {
  items: ApprovalListItem[];
  total: number;
  limit: number;
  offset: number;
};

type ApprovalDetail = {
  approval_id: string;
  target_type: TargetType;
  target_id: string;
  approval_status: ApprovalStatus;
  target_status: string;
  approval_required: boolean;
  reviewed_by: string | null;
  reviewed_at: string | null;
  reason: string | null;
};

type ReviewAction = "approve" | "reject";

const statusOptions: ApprovalStatus[] = ["PENDING", "APPROVED", "REJECTED"];
const targetOptions: Array<{ label: string; value: TargetFilter }> = [
  { label: "전체", value: "all" },
  { label: "메시지 초안", value: "contact_message" },
  { label: "상태 업데이트 후보", value: "status_update_candidate" },
  { label: "Handoff Package", value: "handoff_package_draft" },
];

const statusLabels: Record<ApprovalStatus, string> = {
  PENDING: "승인 대기",
  APPROVED: "승인 완료",
  REJECTED: "반려",
};

const targetLabels: Record<TargetType, string> = {
  contact_message: "메시지",
  status_update_candidate: "상태 후보",
  handoff_package_draft: "Handoff",
};

const safeTargetFields: Record<TargetType, string[]> = {
  contact_message: ["message_purpose", "language_code", "status", "approval_status", "created_at"],
  status_update_candidate: [
    "target_type",
    "target_key",
    "candidate_status",
    "confidence",
    "status",
    "approval_status",
    "created_at",
  ],
  handoff_package_draft: [
    "package_type",
    "case_type",
    "risk_level",
    "handoff_ready",
    "status",
    "approval_status",
    "created_at",
  ],
};

const forbiddenFieldPattern =
  /(korean_text|translated_text|worker_reply|translated_ko|package_json|worker_id|passport|alien|phone|address)/i;

function statusClass(status: string) {
  if (status === "APPROVED") {
    return "approval-badge success";
  }
  if (status === "REJECTED") {
    return "approval-badge danger";
  }
  return "approval-badge pending";
}

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function errorMessage(status: number) {
  if (status === 403) {
    return "접근 권한이 없습니다.";
  }
  if (status === 404) {
    return "승인 요청을 찾을 수 없습니다.";
  }
  if (status === 409) {
    return "이미 처리된 승인 요청입니다.";
  }
  if (status >= 500) {
    return "서버 오류가 발생했습니다.";
  }
  return "요청을 처리하지 못했습니다.";
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      accept: "application/json",
      "Content-Type": "application/json",
      "X-Company-Id": COMPANY_ID,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(errorMessage(response.status));
  }
  return (await response.json()) as T;
}

export function ApprovalsInbox() {
  const [status, setStatus] = useState<ApprovalStatus>("PENDING");
  const [targetType, setTargetType] = useState<TargetFilter>("all");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ApprovalListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selected, setSelected] = useState<ApprovalListItem | null>(null);
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [reviewAction, setReviewAction] = useState<ReviewAction | null>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const limit = 20;

  const query = useMemo(() => {
    const params = new URLSearchParams({
      status,
      limit: String(limit),
      offset: String(offset),
    });
    if (targetType !== "all") {
      params.set("target_type", targetType);
    }
    return params.toString();
  }, [offset, status, targetType]);

  async function loadApprovals() {
    setLoading(true);
    setError(null);
    try {
      const result = await requestJson<ApprovalListResponse>(`/api/v1/approvals?${query}`);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadApprovals();
  }, [query]);

  async function openDetail(item: ApprovalListItem) {
    setSelected(item);
    setDetail(null);
    setError(null);
    try {
      const result = await requestJson<ApprovalDetail>(`/api/v1/approvals/${item.approval_id}`);
      setDetail(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "상세 정보를 불러오지 못했습니다.");
    }
  }

  async function submitReview() {
    if (!selected || !reviewAction) {
      return;
    }
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      await requestJson<ApprovalDetail>(
        `/api/v1/approvals/${selected.approval_id}/${reviewAction}`,
        {
          method: "POST",
          body: JSON.stringify({
            reviewed_by: REVIEWER_ID,
            reason: reason.trim() || (reviewAction === "approve" ? "검토 완료" : "보완 필요"),
          }),
        },
      );
      setNotice(reviewAction === "approve" ? "승인 처리되었습니다." : "반려 처리되었습니다.");
      setReviewAction(null);
      setSelected(null);
      setDetail(null);
      setReason("");
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "처리 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const canGoPrev = offset > 0;
  const canGoNext = offset + limit < total;

  return (
    <section className="approval-page">
      <header className="approval-header">
        <div>
          <span className="kicker">Approvals</span>
          <h2>승인 대기함</h2>
          <p>
            AI가 생성한 메시지 초안, 상태 업데이트 후보, 전문가 전달 초안을 담당자가
            검토하고 승인/반려하는 화면입니다.
          </p>
        </div>
        <div className="approval-safety-note">
          <strong>승인은 외부 실행이 아닙니다.</strong>
          <span>메시지 발송, 상태 반영, 전문가 전달은 별도 단계에서 처리됩니다.</span>
        </div>
      </header>

      <div className="approval-toolbar" aria-label="승인 목록 필터">
        <div className="filter-group">
          <span className="filter-label">상태</span>
          <div className="segmented-control">
            {statusOptions.map((option) => (
              <button
                className={status === option ? "segment active" : "segment"}
                key={option}
                onClick={() => {
                  setStatus(option);
                  setOffset(0);
                }}
                type="button"
              >
                {statusLabels[option]}
              </button>
            ))}
          </div>
        </div>
        <div className="filter-group">
          <span className="filter-label">대상</span>
          <select
            className="approval-select"
            value={targetType}
            onChange={(event) => {
              setTargetType(event.target.value as TargetFilter);
              setOffset(0);
            }}
          >
            {targetOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {(error || notice) && (
        <div className={error ? "approval-alert error" : "approval-alert success"}>
          {error || notice}
        </div>
      )}

      <div className="approval-table-shell">
        <div className="approval-table-meta">
          <strong>{loading ? "불러오는 중" : `${total}건`}</strong>
          <span>페이지 {Math.floor(offset / limit) + 1}</span>
        </div>
        <div className="approval-table-scroll">
          <table className="approval-table">
            <thead>
              <tr>
                <th>유형</th>
                <th>요약</th>
                <th>승인 상태</th>
                <th>대상 상태</th>
                <th>생성일</th>
                <th>검토일</th>
                <th>액션</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.approval_id}>
                  <td>
                    <span className="approval-badge neutral">
                      {targetLabels[item.target_type]}
                    </span>
                  </td>
                  <td>
                    <strong>{item.summary}</strong>
                  </td>
                  <td>
                    <span className={statusClass(item.approval_status)}>
                      {statusLabels[item.approval_status]}
                    </span>
                  </td>
                  <td>{item.target_status}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td>{formatDate(item.reviewed_at)}</td>
                  <td>
                    <div className="approval-actions">
                      <button type="button" onClick={() => void openDetail(item)}>
                        상세 보기
                      </button>
                      <button
                        disabled={item.approval_status !== "PENDING"}
                        type="button"
                        onClick={() => {
                          setSelected(item);
                          setReviewAction("approve");
                          setReason("검토 완료");
                        }}
                      >
                        승인
                      </button>
                      <button
                        disabled={item.approval_status !== "PENDING"}
                        type="button"
                        onClick={() => {
                          setSelected(item);
                          setReviewAction("reject");
                          setReason("");
                        }}
                      >
                        반려
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && items.length === 0 && (
                <tr>
                  <td className="approval-empty" colSpan={7}>
                    조건에 맞는 승인 요청이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="approval-pagination">
          <button
            disabled={!canGoPrev}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            type="button"
          >
            이전
          </button>
          <button
            disabled={!canGoNext}
            onClick={() => setOffset(offset + limit)}
            type="button"
          >
            다음
          </button>
        </div>
      </div>

      {selected && !reviewAction && (
        <aside className="approval-drawer" aria-label="승인 상세">
          <div className="drawer-panel">
            <div className="drawer-header">
              <div>
                <span className="kicker">Detail</span>
                <h3>승인 상세</h3>
              </div>
              <button type="button" onClick={() => setSelected(null)}>
                닫기
              </button>
            </div>
            <dl className="detail-grid">
              <DetailRow label="approval_id" value={selected.approval_id} />
              <DetailRow label="target_type" value={selected.target_type} />
              <DetailRow label="target_id" value={selected.target_id} />
              <DetailRow
                label="approval_status"
                value={detail?.approval_status ?? selected.approval_status}
              />
              <DetailRow label="target_status" value={detail?.target_status ?? selected.target_status} />
              <DetailRow label="summary" value={selected.summary} />
              <DetailRow label="reviewed_by" value={detail?.reviewed_by ?? null} />
              <DetailRow label="reviewed_at" value={detail?.reviewed_at ?? selected.reviewed_at} />
              <DetailRow label="reason" value={detail?.reason ?? null} />
            </dl>
            <h4>대상 요약</h4>
            <dl className="detail-grid">
              {safeTargetFields[selected.target_type].map((field) => (
                <DetailRow key={field} label={field} value={selected.target[field]} />
              ))}
            </dl>
          </div>
        </aside>
      )}

      {selected && reviewAction && (
        <div className="approval-modal" role="dialog" aria-modal="true">
          <div className="modal-panel">
            <h3>
              {reviewAction === "approve"
                ? "이 항목을 승인하시겠습니까?"
                : "반려 사유를 입력하세요."}
            </h3>
            <p>
              승인은 외부 실행이 아닙니다. 메시지 발송, 상태 반영, 전문가 전달은 별도
              단계에서 처리됩니다.
            </p>
            <label className="reason-field">
              <span>reason</span>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder={reviewAction === "approve" ? "검토 완료" : "보완 필요"}
                rows={4}
              />
            </label>
            <div className="modal-actions">
              <button
                disabled={submitting}
                type="button"
                onClick={() => {
                  setReviewAction(null);
                  setReason("");
                }}
              >
                취소
              </button>
              <button disabled={submitting} type="button" onClick={() => void submitReview()}>
                {submitting ? "처리 중" : reviewAction === "approve" ? "승인" : "반려"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string | boolean | null | undefined;
}) {
  if (forbiddenFieldPattern.test(label)) {
    return null;
  }
  return (
    <>
      <dt>{label}</dt>
      <dd>{value === null || value === undefined || value === "" ? "-" : String(value)}</dd>
    </>
  );
}
