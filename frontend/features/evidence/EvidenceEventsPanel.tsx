"use client";

import { useEffect, useState } from "react";
import { getCaseEvidenceEvents } from "../../lib/api";
import type { EvidenceEvent } from "../../types/dailyBriefing";

export function EvidenceEventsPanel({
  caseId,
  companyId = "company_001",
}: {
  caseId: string;
  companyId?: string;
}) {
  const [events, setEvents] = useState<EvidenceEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    getCaseEvidenceEvents(caseId, companyId)
      .then(setEvents)
      .catch((err) => setError(err instanceof Error ? err.message : "Evidence lookup failed"));
  }, [caseId, companyId]);

  return (
    <section className="evidence-panel">
      <div className="evidence-panel-header">
        <p className="evidence-panel-eyebrow">Evidence Log</p>
        <h1>케이스 판단 근거 이벤트</h1>
        <p className="evidence-panel-meta">case_id: {caseId || "없음"}</p>
        <p className="evidence-panel-meta">company_id: {companyId}</p>
        {error ? <p className="evidence-panel-error">{error}</p> : null}
      </div>
      {events.map((event) => (
        <article className="evidence-event-card" key={event.event_id}>
          <p className="evidence-event-type">
            {event.event_type} / {event.node_name}
          </p>
          <p className="evidence-event-summary">{event.summary}</p>
          <div className="evidence-event-meta">
            <span>actor: {event.actor_type}</span>
            <span>hash: {event.redacted_output_hash ?? "n/a"}</span>
            <span>citations: {event.citation_ids.length ? event.citation_ids.join(", ") : "없음"}</span>
          </div>
        </article>
      ))}
      {events.length === 0 && !error ? (
        <p className="evidence-panel-empty">이 케이스의 판단 근거 이벤트가 없습니다.</p>
      ) : null}
    </section>
  );
}
