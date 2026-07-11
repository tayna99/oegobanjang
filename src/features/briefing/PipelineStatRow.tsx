import { EXECUTED_WEEKLY_MOCK } from '@/mocks/fixtures';
import { pipelineCounts } from '@/lib/pipeline';
import type { CaseCard } from '@/types';

// 파이프라인 스탯 로우 — reference/design-system/외고반장 Mobile.dc.html §2a(43~49행) 이식(M2.6.1).
// 숫자는 누적 깔때기(lib/pipeline)에서 파생. 색은 파이프라인 단계 칩 토큰과 동일 계열.
export function PipelineStatRow({ cards }: { cards: CaseCard[] }) {
  const counts = pipelineCounts(cards);
  const stats = [
    { label: '감지', value: counts.detected, tone: 'text-detected' },
    { label: '근거 수집', value: counts.collecting, tone: 'text-approval' },
    { label: '초안', value: counts.drafted, tone: 'text-draft' },
    { label: '승인 대기', value: counts.awaitingApproval, tone: 'text-warning' },
    { label: '실행(주)', value: EXECUTED_WEEKLY_MOCK, tone: 'text-success' },
  ];

  return (
    <div className="flex rounded-in border border-hairline bg-canvas px-2 py-2.5" aria-label="에이전트 파이프라인">
      {stats.map(({ label, value, tone }) => (
        <div key={label} className="flex flex-1 flex-col items-center gap-0.5">
          <span className={`text-body2 font-bold tabular-nums ${tone}`}>{value}</span>
          <span className="text-pc-2xs text-subtle">{label}</span>
        </div>
      ))}
    </div>
  );
}
