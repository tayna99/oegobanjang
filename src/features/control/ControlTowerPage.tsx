import { useEffect, useMemo } from 'react';
import { Chip } from '@/components/Chip';
import { cn } from '@/lib/cn';
import { AUDIT_TYPE_LABEL, AUDIT_TYPE_TONE, mergedAuditLog } from '@/lib/audit';
import { sortCaseList } from '@/lib/cases';
import { AGENT_STAGE_LABELS } from '@/lib/caseStage';
import {
  PIPELINE_DELTAS,
  WEEKLY_ACTIVE_TREND,
  WEEKLY_TREND_RANGE,
  controlTowerKpis,
  rowAction,
} from '@/lib/controlTower';
import { agentStageTone, severityTone } from '@/lib/chipTone';
import { dDayLabel, dDayTextClass } from '@/lib/dday';
import { useNav } from '@/lib/nav';
import { pipelineStats } from '@/lib/pipeline';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { CaseCard, Severity } from '@/types';

// PC 컨트롤 타워(§3a) — reference/design-system/외고반장 PC.dc.html §3a(29~232행) 이식(2.5.6).
// 파이프라인 타일·KPI·활성 추이·우선 처리 큐 + 우측 활동/감사 레일. 데스크톱 전용.
// KPI·큐는 스토어에서 파생(mock은 지난주 추이·오늘 델타뿐). C10: 고위험 행 액션은 "검토".

const SEVERITY_LABEL: Record<Severity, string> = { CRITICAL: '긴급', HIGH: '높음', MEDIUM: '중간', LOW: '낮음' };
const SECTION_TITLE = 'text-caption1 font-bold tracking-wide text-muted';

function PipelineTile({
  label,
  value,
  delta,
  tone,
  emphasized,
}: {
  label: string;
  value: number;
  delta: string;
  tone: string;
  emphasized?: boolean;
}) {
  return (
    <div
      className={cn(
        'flex flex-1 flex-col gap-1 rounded-in border bg-canvas px-3.5 py-3',
        emphasized ? 'border-primary/40 shadow-step-current' : 'border-hairline',
      )}
    >
      <span className="text-pc-2xs text-subtle">{label}</span>
      <span className={cn('text-heading1 font-bold tabular-nums', tone)}>{value}</span>
      <span className="text-pc-2xs text-dim">{delta}</span>
    </div>
  );
}

function KpiTile({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="flex min-w-[130px] flex-col gap-1 rounded-in border border-hairline bg-canvas px-3.5 py-3">
      <span className="text-pc-2xs text-subtle">{label}</span>
      <span className={cn('text-heading2 font-bold tabular-nums', tone)}>{value}</span>
    </div>
  );
}

function TrendChart() {
  const max = Math.max(...WEEKLY_ACTIVE_TREND);
  const min = Math.min(...WEEKLY_ACTIVE_TREND);
  const span = max - min || 1;
  const points = WEEKLY_ACTIVE_TREND.map((v, i) => {
    const x = (i / (WEEKLY_ACTIVE_TREND.length - 1)) * 318;
    const y = 30 - ((v - min) / span) * 28; // 낮은 y = 높은 값
    return `${x.toFixed(0)},${y.toFixed(0)}`;
  }).join(' ');
  return (
    <div className="flex flex-1 flex-col gap-2 rounded-in border border-hairline bg-canvas px-3.5 py-3">
      <div className="flex items-baseline justify-between">
        <span className={SECTION_TITLE}>활성 케이스 추이 (7일)</span>
        <span className="text-pc-2xs text-dim">{WEEKLY_TREND_RANGE}</span>
      </div>
      <svg viewBox="0 0 320 34" className="h-9 w-full" aria-hidden="true">
        <polyline points={points} fill="none" stroke="var(--color-primary-normal)" strokeWidth="2" />
      </svg>
    </div>
  );
}

function PriorityRow({ card, onOpen }: { card: CaseCard; onOpen: (id: string) => void }) {
  const action = rowAction(card);
  const stage = card.agentStage ?? 'detected';
  const completeness = card.evidenceCompleteness ?? 0;
  return (
    <li className="grid grid-cols-[64px_150px_1fr_60px_120px_100px_64px_72px] items-center gap-2 border-b border-hairline px-3 py-2.5 last:border-none">
      <span>
        <Chip tone={severityTone(card.severity)}>{SEVERITY_LABEL[card.severity]}</Chip>
      </span>
      <span className="flex min-w-0 flex-col">
        <span className="truncate text-pc-sm font-semibold text-ink">{card.workerRef?.displayName ?? card.title}</span>
        <span className="truncate text-pc-2xs text-subtle">
          {card.workerRef ? `${card.workerRef.team} · ${card.workerRef.nationality}` : card.caseCode}
        </span>
      </span>
      <span className="min-w-0 truncate text-caption1 text-ink">{card.title}</span>
      <span className={cn('text-pc-xs font-bold tabular-nums', dDayTextClass(card.dDay))}>
        {card.dDay !== undefined ? dDayLabel(card.dDay) : '—'}
      </span>
      <span>
        <Chip tone={agentStageTone(stage)}>{AGENT_STAGE_LABELS[stage]}</Chip>
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-[3px] flex-1 overflow-hidden rounded-full bg-neutbg">
          <span className="block h-full rounded-full bg-primary" style={{ width: `${completeness}%` }} />
        </span>
        <span className="shrink-0 text-pc-2xs tabular-nums text-dim">{completeness}%</span>
      </span>
      <span className="truncate text-caption1 text-subtle">{card.assignee ?? '—'}</span>
      <span className="text-right">
        <button
          type="button"
          onClick={() => onOpen(card.caseId)}
          className={cn(
            'rounded-btn-sm px-2.5 py-1 text-pc-xs font-semibold transition-colors duration-btn ease-v2',
            action.kind === 'approve' ? 'bg-primary text-white' : 'text-ink shadow-outline hover:bg-surface',
          )}
        >
          {action.label}
        </button>
      </span>
    </li>
  );
}

function ActivityRail() {
  const events = useEvidenceStore((s) => s.events);
  const nav = useNav();
  const log = useMemo(() => mergedAuditLog(events), [events]);
  const activity = log.slice(0, 5);
  const audit = log.slice(0, 3);
  const time = (iso: string) => iso.slice(11, 16);

  return (
    <aside aria-label="활동·감사 레일" className="flex w-[370px] shrink-0 flex-col gap-5 overflow-y-auto border-l border-hairline bg-canvas p-5">
      <section className="flex flex-col gap-2">
        <span className={SECTION_TITLE}>실시간 에이전트 활동</span>
        <ul className="flex flex-col gap-2">
          {activity.map((e) => (
            <li key={e.id} className="flex items-start gap-2">
              <span className="w-9 shrink-0 text-pc-2xs text-dim tabular-nums">{time(e.at)}</span>
              <Chip tone={AUDIT_TYPE_TONE[e.type]}>{AUDIT_TYPE_LABEL[e.type]}</Chip>
              <span className="min-w-0 flex-1 text-pc-xs leading-snug text-ink">{e.summary}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className={SECTION_TITLE}>감사 로그</span>
          <button type="button" onClick={() => nav.toEvidence()} className="text-pc-2xs font-semibold text-primary">
            전체 보기
          </button>
        </div>
        <ul className="flex flex-col gap-1.5">
          {audit.map((e) => (
            <li key={e.id} className="flex flex-col gap-0.5 rounded-in border border-hairline px-2.5 py-2">
              <div className="flex items-center gap-1.5">
                {e.evidenceRef && <span className="text-pc-2xs font-bold text-primary">{e.evidenceRef}</span>}
                <Chip tone={AUDIT_TYPE_TONE[e.type]}>{AUDIT_TYPE_LABEL[e.type]}</Chip>
                <span className="ml-auto text-pc-2xs text-dim tabular-nums">{e.actor ?? 'system'}</span>
              </div>
              <span className="text-pc-xs text-ink">{e.summary}</span>
            </li>
          ))}
        </ul>
      </section>

      <p className="mt-auto text-pc-2xs text-subtle">INSERT-only · 원문 PII 미저장 (해시만 기록)</p>
    </aside>
  );
}

export function ControlTowerPage() {
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const cards = useMemo(() => Object.values(cases), [cases]);
  const counts = useMemo(() => pipelineStats(cards), [cards]);
  const kpis = useMemo(() => controlTowerKpis(cards, CASE_SHEETS), [cards]);
  const priority = useMemo(() => sortCaseList(cards), [cards]);

  return (
    <section aria-label="컨트롤 타워" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <div className="flex min-w-0 flex-1 flex-col gap-5 overflow-y-auto p-6">
        <header className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-0.5">
            <h1 className="text-heading2 font-bold text-ink">컨트롤 타워</h1>
            <p className="text-caption1 text-subtle">7월 10일 (금) 08:00 브리핑 생성 · brf_company_001_2026-07-10</p>
          </div>
        </header>

        <div className="flex gap-2.5" aria-label="에이전트 파이프라인">
          <PipelineTile label="감지됨" value={counts.detected} delta={PIPELINE_DELTAS.detected} tone="text-detected" />
          <PipelineTile label="근거 수집 완료" value={counts.collecting} delta={PIPELINE_DELTAS.collecting} tone="text-approval" />
          <PipelineTile label="초안 생성 완료" value={counts.drafted} delta={PIPELINE_DELTAS.drafted} tone="text-draft" />
          <PipelineTile label="승인 대기" value={counts.awaitingApproval} delta={PIPELINE_DELTAS.awaitingApproval} tone="text-warning" emphasized />
          <PipelineTile label="실행 완료 (주간)" value={counts.executedWeekly} delta={PIPELINE_DELTAS.executedWeekly} tone="text-success" />
        </div>

        <div className="flex gap-2.5" aria-label="KPI">
          <KpiTile label="활성 케이스" value={kpis.activeCases} tone="text-ink" />
          <KpiTile label="고위험 (C+H)" value={kpis.highRisk} tone="text-critical" />
          <KpiTile label="D-day 임박 (≤7일)" value={kpis.dDayImminent} tone="text-warning" />
          <KpiTile label="근거 부족" value={kpis.evidenceShort} tone="text-success" />
          <TrendChart />
        </div>

        <section className="flex flex-col gap-2" aria-label="우선 처리 케이스">
          <div className="flex items-baseline justify-between">
            <span className={SECTION_TITLE}>우선 처리 케이스</span>
            <span className="text-pc-2xs text-dim">정렬: 위험도 × D-day</span>
          </div>
          <div className="overflow-hidden rounded-in border border-hairline bg-canvas">
            <div className="grid grid-cols-[64px_150px_1fr_60px_120px_100px_64px_72px] items-center gap-2 border-b border-hairline bg-surface px-3 py-2 text-pc-2xs font-bold text-subtle">
              <span>위험</span>
              <span>근로자</span>
              <span>케이스</span>
              <span>D-day</span>
              <span>에이전트 단계</span>
              <span>근거 완성도</span>
              <span>담당</span>
              <span className="text-right">액션</span>
            </div>
            <ul>
              {priority.map((card) => (
                <PriorityRow key={card.caseId} card={card} onOpen={(id) => nav.toCase(id)} />
              ))}
            </ul>
          </div>
        </section>

        <p className="flex items-center gap-1.5 text-pc-2xs text-subtle">
          승인 전에는 외부 발송이 차단됩니다. 승인은 케이스 단위로만 가능합니다.
        </p>
      </div>

      <ActivityRail />
    </section>
  );
}
