"use client";

import { useEffect, useMemo, useState } from "react";

import type { DailyBriefingItem, NextAction } from "../../types/dailyBriefing";
import { DailyBriefingChatPanel } from "./DailyBriefingChatPanel";
import { useDailyBriefingWorkflow } from "./useDailyBriefingWorkflow";

const riskTypeLabel: Record<DailyBriefingItem["risk_type"], string> = {
  candidate_readiness: "후보자 입국 전 서류",
  contract_visa_conflict: "계약 종료 확인",
  missing_document: "서류 보완 필요",
  quota_review: "신규 채용 준비",
  reporting_deadline: "고용변동 신고기한",
  visa_expiry: "체류기간 연장 서류",
};

const taskIconByRisk: Record<DailyBriefingItem["risk_type"], string> = {
  candidate_readiness: "□",
  contract_visa_conflict: "▤",
  missing_document: "□",
  quota_review: "♙",
  reporting_deadline: "!",
  visa_expiry: "□",
};

const statusLabel: Record<NextAction["status"], string> = {
  approved: "승인됨",
  blocked: "차단",
  cancelled: "취소",
  completed: "완료",
  pending_approval: "승인 대기",
  rejected: "반려",
  revision_requested: "수정 요청",
};

function timingLabel(item: DailyBriefingItem) {
  if (item.risk_timing_label) {
    return item.risk_timing_label;
  }
  if (item.expired) {
    return `D+${item.days_overdue ?? 0}`;
  }
  if (item.d_day !== null) {
    return `D-${item.d_day}`;
  }
  return "이번 주";
}

function rowStatus(actions: NextAction[]) {
  const primary = actions[0];
  if (!primary) {
    return "응답 도착";
  }
  return statusLabel[primary.status] ?? primary.status;
}

function nextActionLabel(actions: NextAction[]) {
  const action = actions[0];
  if (!action) {
    return "응답 요약";
  }
  if (action.action_type === "request_document") {
    return "초안 보기";
  }
  return "승인 요청";
}

function buildSummaryCards({
  items,
  actions,
}: {
  items: DailyBriefingItem[];
  actions: NextAction[];
}) {
  const byRisk = (riskType: DailyBriefingItem["risk_type"]) =>
    items.filter((item) => item.risk_type === riskType).length;
  return [
    {
      icon: "◷",
      label: "체류기간 임박",
      tone: "danger",
      unit: "명",
      value: byRisk("visa_expiry"),
    },
    {
      icon: "□",
      label: "서류 보완 필요",
      tone: "orange",
      unit: "건",
      value: byRisk("missing_document"),
    },
    {
      icon: "♙",
      label: "신규 채용 준비",
      tone: "green",
      unit: "건",
      value: byRisk("quota_review"),
    },
    {
      icon: "▱",
      label: "컨택 대기",
      tone: "purple",
      unit: "건",
      value: actions.filter((action) => action.action_type === "request_document").length,
    },
    {
      icon: "▰",
      label: "응답 도착",
      tone: "blue",
      unit: "건",
      value: items.filter((item) => item.risk_type === "contract_visa_conflict").length,
    },
    {
      icon: "◇",
      label: "승인 대기",
      tone: "amber",
      unit: "건",
      value: actions.filter((action) => action.status === "pending_approval").length,
    },
    {
      icon: "☑",
      label: "행정사 검토 준비",
      tone: "indigo",
      unit: "건",
      value: actions.filter((action) => action.action_type === "create_handoff").length,
    },
  ];
}

export function DailyBriefingPanel() {
  const {
    approve: handleApprove,
    briefing,
    citationChunk,
    citationSource,
    citationValidation,
    companyId,
    date,
    deliveryJob,
    documentDraft,
    error,
    exportArtifacts,
    loading,
    mockDispatch: handleMockDispatch,
    openCitation: handleOpenCitation,
    openDocumentDraft: handleOpenDocumentDraft,
    openHandoffPreview: handleOpenPreview,
    preview,
    reject: handleReject,
    requestActionRevision: handleRevision,
    runBriefing: handleRunBriefing,
    setCitationChunk,
    setCitationSource,
    setCitationValidation,
    setDeliveryJob,
    setDocumentDraft,
    setPreview,
  } = useDailyBriefingWorkflow();
  const [chatOpen, setChatOpen] = useState(false);
  const [showExportArtifacts, setShowExportArtifacts] = useState(false);

  useEffect(() => {
    void handleRunBriefing();
  }, [handleRunBriefing]);

  useEffect(() => {
    if (exportArtifacts.length) {
      setShowExportArtifacts(true);
    }
  }, [exportArtifacts.length]);

  const items = briefing?.items ?? [];
  const actions = briefing?.recommended_actions ?? [];
  const summaryCards = useMemo(() => buildSummaryCards({ actions, items }), [actions, items]);
  const visibleItems = items.slice(0, 8);

  return (
    <section className="ops-console">
      <div className="ops-announcement">
        <div className="ops-agent-mark">반</div>
        <div>
          <strong>오늘 브리핑이 준비되었습니다</strong>
          <p>
            외고반장이 {items.length || 0}개 케이스를 정리했습니다. 즉시 확인{" "}
            {briefing?.risk_summary.critical_count ?? 0}건, 우선 확인{" "}
            {briefing?.risk_summary.high_count ?? 0}건, 승인 대기{" "}
            {actions.filter((action) => action.status === "pending_approval").length}건. 모든 판단의 근거는
            항목 클릭으로 확인할 수 있습니다.
          </p>
        </div>
        <span className="ops-announcement-time">오늘 08:00</span>
        <button className="ops-secondary-button" disabled={loading} onClick={handleRunBriefing} type="button">
          ↻ 다시 생성
        </button>
      </div>

      {error ? <div className="ops-error">API 연결 실패 · {error}</div> : null}

      <div className="ops-summary-grid" aria-label="오늘 브리핑 지표">
        {summaryCards.map((card) => (
          <article className="ops-summary-card" data-tone={card.tone} key={card.label}>
            <span className="ops-summary-icon">{card.icon}</span>
            <span className="ops-summary-label">{card.label}</span>
            <strong>
              {card.value}
              <small>{card.unit}</small>
            </strong>
          </article>
        ))}
      </div>

      <div className="ops-section-title">
        <div>
          <h2>오늘의 업무 큐</h2>
          <span>{visibleItems.length}건</span>
        </div>
        <div className="ops-toolbar">
          <button type="button">필터</button>
          <button type="button">기한 임박 순⌄</button>
        </div>
      </div>

      <div className="ops-table-shell">
        <div className="ops-table-header">
          <span />
          <span>업무</span>
          <span>대상</span>
          <span>상태</span>
          <span>기한</span>
          <span>다음 처리</span>
          <span />
        </div>
        {loading && !briefing ? <div className="ops-empty-row">브리핑을 불러오는 중입니다...</div> : null}
        {!loading && !visibleItems.length ? (
          <div className="ops-empty-row">오늘 표시할 업무가 없습니다.</div>
        ) : null}
        {visibleItems.map((item) => {
          const rowActions = actions.filter((action) => item.next_action_ids.includes(action.action_id));
          const primaryAction = rowActions[0];
          return (
            <article className="ops-task-row" key={item.item_id}>
              <span className="ops-checkbox" aria-hidden="true" />
              <div className="ops-task-title">
                <span className="ops-task-icon">{taskIconByRisk[item.risk_type]}</span>
                <button
                  onClick={() => (item.citation_ids[0] ? handleOpenCitation(item.citation_ids[0]) : undefined)}
                  type="button"
                >
                  {item.case_title ?? riskTypeLabel[item.risk_type]}
                </button>
              </div>
              <span className="ops-subject">
                {item.subject_display_name ?? item.subject_display_id ?? item.subject_id}
              </span>
              <span className="ops-status">{rowStatus(rowActions)}</span>
              <strong className={item.expired || (item.d_day ?? 99) <= 30 ? "ops-deadline urgent" : "ops-deadline"}>
                {timingLabel(item)}
              </strong>
              <div className="ops-row-actions">
                {primaryAction ? (
                  <button
                    onClick={() =>
                      primaryAction.action_type === "request_document"
                        ? handleOpenDocumentDraft(primaryAction)
                        : handleOpenPreview(primaryAction)
                    }
                    type="button"
                  >
                    {nextActionLabel(rowActions)}
                  </button>
                ) : (
                  <button
                    onClick={() => (item.citation_ids[0] ? handleOpenCitation(item.citation_ids[0]) : undefined)}
                    type="button"
                  >
                    근거 보기
                  </button>
                )}
              </div>
              <span className="ops-more">⋮</span>
            </article>
          );
        })}
      </div>

      <div className="ops-lower-grid">
        <section className="ops-panel">
          <div className="ops-panel-heading">
            <h3>승인 대기 작업</h3>
            <span>{actions.filter((action) => action.status === "pending_approval").length}건</span>
          </div>
          <div className="ops-action-list">
            {actions.slice(0, 5).map((action) => (
              <article className="ops-action-card" key={action.action_id}>
                <div>
                  <strong>{action.label}</strong>
                  <p>{action.action_type === "request_document" ? "다국어 초안" : "행정사 검토 패키지"}</p>
                </div>
                <div className="ops-action-buttons">
                  <button
                    disabled={action.status !== "pending_approval"}
                    onClick={() => handleApprove(action)}
                    type="button"
                  >
                    승인
                  </button>
                  <button
                    disabled={action.status !== "pending_approval"}
                    onClick={() => handleRevision(action)}
                    type="button"
                  >
                    수정
                  </button>
                  <button
                    disabled={action.status !== "pending_approval"}
                    onClick={() => handleReject(action)}
                    type="button"
                  >
                    반려
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="ops-panel">
          <div className="ops-panel-heading">
            <h3>근거 / Evidence</h3>
            <span>{briefing?.citation_summaries.length ?? 0}개</span>
          </div>
          <div className="ops-evidence-list">
            {(briefing?.citation_summaries ?? []).slice(0, 5).map((source) => (
              <button key={source.citation_id} onClick={() => handleOpenCitation(source.citation_id)} type="button">
                <strong>{source.title}</strong>
                <span>{source.source}</span>
              </button>
            ))}
          </div>
        </section>
      </div>

      {preview ? (
        <DetailDrawer title="행정사 검토 패키지" onClose={() => setPreview(null)}>
          <pre>{JSON.stringify(preview.content_redacted, null, 2)}</pre>
          <p>검토용 초안입니다. 외부 전달은 수행하지 않았습니다.</p>
        </DetailDrawer>
      ) : null}

      {documentDraft ? (
        <DetailDrawer title="서류 요청 메시지 초안" onClose={() => setDocumentDraft(null)}>
          <h4>한국어 원문</h4>
          <p>{documentDraft.korean_text}</p>
          <h4>번역 초안</h4>
          <p>{documentDraft.translated_text}</p>
          <p>승인 전에는 외부로 발송되지 않습니다.</p>
        </DetailDrawer>
      ) : null}

      {deliveryJob ? (
        <DetailDrawer title="외부 전달 경계" onClose={() => setDeliveryJob(null)}>
          <p>
            상태: {deliveryJob.status}. Provider: {deliveryJob.provider}. 실제 외부 발송 여부:{" "}
            {String(deliveryJob.external_send_performed)}.
          </p>
          {deliveryJob.status === "pending_manual_dispatch" ? (
            <button className="ops-primary-button" onClick={handleMockDispatch} type="button">
              Mock dispatch path 확인
            </button>
          ) : null}
        </DetailDrawer>
      ) : null}

      {exportArtifacts.length && showExportArtifacts ? (
        <DetailDrawer title="Export artifact history" onClose={() => setShowExportArtifacts(false)}>
          {exportArtifacts.map((artifact) => (
            <p key={artifact.artifact_id}>
              {artifact.format.toUpperCase()} draft · {artifact.content_hash}
            </p>
          ))}
        </DetailDrawer>
      ) : null}

      {citationChunk && citationSource && citationValidation ? (
        <DetailDrawer
          title="판단 근거"
          onClose={() => {
            setCitationChunk(null);
            setCitationSource(null);
            setCitationValidation(null);
          }}
        >
          <h4>{citationSource.title}</h4>
          <p>{citationChunk.chunk_text}</p>
          <p>검증 상태: {citationValidation.validation_status}</p>
        </DetailDrawer>
      ) : null}

      {chatOpen ? (
        <div className="ops-chat-drawer">
          <div className="ops-chat-backdrop" onClick={() => setChatOpen(false)} />
          <div className="ops-chat-panel">
            <button className="ops-chat-close" onClick={() => setChatOpen(false)} type="button">
              닫기
            </button>
            <DailyBriefingChatPanel
              companyId={companyId}
              date={date}
              onOpenCitation={handleOpenCitation}
              onOpenDocumentDraft={handleOpenDocumentDraft}
              onOpenHandoffPreview={handleOpenPreview}
            />
          </div>
        </div>
      ) : null}

      <button className="ops-floating-agent" onClick={() => setChatOpen(true)} type="button">
        ✦ AI 반장
      </button>
    </section>
  );
}

function DetailDrawer({
  children,
  title,
  onClose,
}: {
  children: React.ReactNode;
  title: string;
  onClose: () => void;
}) {
  return (
    <aside className="ops-drawer">
      <div className="ops-drawer-card">
        <div className="ops-drawer-heading">
          <h3>{title}</h3>
          <button onClick={onClose} type="button">
            닫기
          </button>
        </div>
        <div className="ops-drawer-body">{children}</div>
      </div>
    </aside>
  );
}
