import { Chip } from '@/components/Chip';
import { AGENT_STAGE_LABELS_SHORT } from '@/lib/caseStage';
import { agentStageTone } from '@/lib/chipTone';
import { dDayLabel, dDayTone, type DDayTone } from '@/lib/dday';
import { cn } from '@/lib/cn';
import type { CaseCard } from '@/types';

// 에이전트 진행 중 리스트 — reference/design-system/외고반장 Mobile.dc.html §2a(77~81행) 이식(M2.6.1).
// 행 = 단계 칩 + "근로자 · 업무" + D-day. 행 탭 → 2b 검토 페이지(읽기용 컨텍스트).
export interface AgentProgressListProps {
  cards: CaseCard[];
  onOpenCase: (caseId: string) => void;
}

const DDAY_TEXT: Record<DDayTone, string> = {
  critical: 'text-critical',
  high: 'text-warning',
  medium: 'text-medium',
  neutral: 'text-muted',
};

export function AgentProgressList({ cards, onOpenCase }: AgentProgressListProps) {
  if (cards.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-in border border-hairline bg-canvas">
      {cards.map((card) => {
        const stage = card.agentStage ?? 'detected';
        return (
          <button
            key={card.caseId}
            type="button"
            aria-label={card.title}
            onClick={() => onOpenCase(card.caseId)}
            className="flex min-h-12 w-full items-center gap-2.5 border-b border-hairline px-3.5 py-2.5 text-left last:border-none active:bg-surface"
          >
            <Chip tone={agentStageTone(stage)}>{AGENT_STAGE_LABELS_SHORT[stage]}</Chip>
            <span className="min-w-0 flex-1 truncate text-label1 text-ink">
              {card.workerRef ? `${card.workerRef.displayName} · ` : ''}
              {card.title}
            </span>
            <span
              className={cn(
                'shrink-0 text-pc-xs font-bold tabular-nums',
                card.dDay !== undefined ? DDAY_TEXT[dDayTone(card.dDay)] : 'text-faint',
              )}
            >
              {card.dDay !== undefined ? dDayLabel(card.dDay) : '—'}
            </span>
          </button>
        );
      })}
    </div>
  );
}
