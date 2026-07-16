import { useState } from 'react';
import { Button } from '@/components/Button';
import { IconLock } from '@/components/icons';
import { PcOnlyNotice } from '@/components/PcOnlyNotice';
import { useNav } from '@/lib/nav';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { DISPATCH_HISTORY, DISPATCH_QUEUE, type DispatchItem } from '@/mocks/dispatch';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

// 발송 실행 큐(PC 4d, 순신규) — reference/design-system/외고반장 PC_4a-4f(신규티어).dc.html
// §4d 이식. "승인된 것만 이 화면에 도착 · mock dispatch · 실행도 evidence 기록." 큐 자체는
// 각본 기반 고정 데이터(mocks/dispatch.ts) — 실제 승인 파이프라인과 자동 연동하지 않는다
// (승인 완료→큐 자동 반영은 후속 확장, GOTCHAS "필요한 만큼만"). 실행 버튼을 누르면
// evidence(dispatch_executed)만 기록하고, 실제 발송 어댑터는 없다(mock).
const ACTION_LABEL: Record<DispatchItem['actionKind'], string> = { dispatch: '발송 실행 (mock)', link_issue: '링크 발급' };

function DispatchQueueWorkbench() {
  const appendEvidence = useEvidenceStore((s) => s.append);
  const events = useEvidenceStore((s) => s.events);
  const [executedIds, setExecutedIds] = useState<Set<string>>(new Set());

  const waiting = DISPATCH_QUEUE.filter((item) => !executedIds.has(item.id));
  const recentEvents = events
    .filter((e) => e.type === 'dispatch_executed')
    .slice()
    .reverse();

  const onExecute = (item: DispatchItem) => {
    appendEvidence({
      id: `dispatch-${item.id}-${Date.now()}`,
      type: 'dispatch_executed',
      at: new Date().toISOString(),
      caseId: item.caseId,
      evidenceRef: item.evidenceRef,
      summary: `${item.workerName} · ${item.actionLabel} 실행`,
      actor: '김담당',
    });
    setExecutedIds((prev) => new Set(prev).add(item.id));
  };

  return (
    <section aria-label="발송 실행 큐" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <section className="flex min-w-0 flex-1 flex-col gap-5 overflow-y-auto p-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-heading2 font-bold text-ink">발송 실행</h1>
          <p className="text-caption1 text-subtle">실행 대기 {waiting.length}건 · 오늘 실행 {DISPATCH_HISTORY.length}건</p>
        </header>

        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">실행 대기 — 승인 완료</span>
          {waiting.length === 0 ? (
            <p className="rounded-in border border-hairline px-3.5 py-4 text-caption1 text-muted">
              실행 대기 중인 항목이 없습니다.
            </p>
          ) : (
            <ul className="overflow-hidden rounded-in border border-hairline">
              {waiting.map((item) => (
                <li key={item.id} className="flex items-center gap-3 border-b border-hairline px-3.5 py-3 last:border-none">
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="text-pc-sm font-semibold text-ink">{item.workerName}</span>
                    <span className="truncate text-pc-xs text-subtle">{item.actionLabel}</span>
                    <span className="text-pc-2xs text-faint">{item.approvedAt} · {item.approvedBy}</span>
                  </div>
                  <span className="shrink-0 text-pc-2xs text-muted">{item.channel}</span>
                  <span className="shrink-0 text-pc-2xs tabular-nums text-faint">{item.evidenceRef}</span>
                  <Button variant="outline" size="sm" className="shrink-0" onClick={() => onExecute(item)}>
                    {ACTION_LABEL[item.actionKind]}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">오늘 실행됨</span>
          <ul className="overflow-hidden rounded-in border border-hairline">
            {DISPATCH_HISTORY.map((item) => (
              <li key={item.id} className="flex items-center gap-3 border-b border-hairline px-3.5 py-3 last:border-none">
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="text-pc-sm font-semibold text-ink">{item.workerName}</span>
                  <span className="truncate text-pc-xs text-subtle">{item.actionLabel}</span>
                  <span className="text-pc-2xs text-faint">{item.timeline}</span>
                </div>
                <span className="shrink-0 text-pc-2xs text-muted">{item.channel}</span>
                <span className="shrink-0 text-pc-2xs tabular-nums text-faint">{item.evidenceRef}</span>
                <span className="shrink-0 text-pc-2xs font-semibold text-success">{item.outcome}</span>
              </li>
            ))}
          </ul>
        </section>
      </section>

      <aside aria-label="실행 규칙" className="flex w-[320px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-hairline bg-canvas p-4">
        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">실행 규칙</span>
          <ul className="flex flex-col gap-1.5 text-pc-xs leading-relaxed text-ink">
            <li>· 승인 완료된 액션만 이 큐에 도착합니다.</li>
            <li>· MVP는 mock adapter — 실제 전송 없이 전달 흐름과 audit trail만 검증합니다.</li>
            <li>· 실행 자체도 evidence 이벤트(dispatch_executed)로 남습니다.</li>
          </ul>
        </section>

        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">최근 실행 이벤트</span>
          {recentEvents.length === 0 ? (
            <p className="text-pc-xs text-faint">이번 세션에서 실행한 이벤트가 없습니다.</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {recentEvents.map((e) => (
                <li key={e.id} className="text-pc-2xs text-muted">
                  {e.summary} · {e.evidenceRef}
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="mt-auto flex items-center gap-1.5 rounded-in bg-surface px-2.5 py-2 text-pc-2xs text-muted">
          <IconLock width={11} height={11} className="shrink-0 text-subtle" />
          <span>승인 없는 발송 0건 — 구조적으로 차단됩니다.</span>
        </div>
      </aside>
    </section>
  );
}

export function DispatchQueuePage() {
  const isDesktop = useIsDesktop();
  const nav = useNav();
  const role = useRoleStore((s) => s.role);

  if (!isDesktop) {
    return <PcOnlyNotice title="발송 실행 큐는 PC에서 이용해 주세요" onBack={() => nav.toCases()} />;
  }

  if (role !== 'manager') {
    return (
      <div className="flex h-[calc(100dvh-4rem)] items-center justify-center p-6">
        <p className="text-body2 text-muted">발송 실행 큐는 담당자 권한으로만 이용할 수 있습니다.</p>
      </div>
    );
  }

  return <DispatchQueueWorkbench />;
}
