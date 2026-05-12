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
    if (!caseId) {
      return;
    }
    getCaseEvidenceEvents(caseId, companyId)
      .then(setEvents)
      .catch((err) => setError(err instanceof Error ? err.message : "Evidence lookup failed"));
  }, [caseId, companyId]);

  return (
    <section className="mx-auto flex max-w-5xl flex-col gap-4 px-6 py-10">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
          Evidence Log
        </p>
        <h1 className="mt-3 text-3xl font-black text-slate-950">케이스 판단 근거 이벤트</h1>
        <p className="mt-3 text-sm text-slate-600">case_id: {caseId || "없음"}</p>
        <p className="mt-1 text-sm text-slate-600">company_id: {companyId}</p>
        {error ? <p className="mt-4 text-sm font-semibold text-red-700">{error}</p> : null}
      </div>
      {events.map((event) => (
        <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm" key={event.event_id}>
          <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
            {event.event_type} / {event.node_name}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{event.summary}</p>
          <div className="mt-3 grid gap-1 text-xs text-slate-500">
            <p>actor: {event.actor_type}</p>
            <p>hash: {event.redacted_output_hash ?? "n/a"}</p>
            <p>citations: {event.citation_ids.length ? event.citation_ids.join(", ") : "없음"}</p>
          </div>
        </article>
      ))}
    </section>
  );
}
