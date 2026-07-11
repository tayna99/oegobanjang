import type { RunStep } from '@/mocks/runs';
import { cn } from '@/lib/cn';

export interface StepTimelineProps {
  steps: RunStep[];
}

const KIND_LABEL: Record<RunStep['kind'], string> = {
  thinking: '판단',
  tool_call: '도구 실행',
  guardrail: '가드레일',
  handoff: '핸드오프',
  replan: '재계획',
};

// GOTCHAS: "가드레일은 숨기지 않고 스텝으로 노출 — 신뢰 자산" — 다른 스텝과
// 시각적으로 구분(경고 톤)되도록 렌더한다.
export function StepTimeline({ steps }: StepTimelineProps) {
  return (
    <ol className="flex flex-col gap-2.5">
      {steps.map((step, index) => (
        <li
          key={index}
          className={cn(
            'rounded-in border p-3',
            step.kind === 'guardrail' ? 'border-warning bg-warnbg' : 'border-hairline bg-surface',
          )}
        >
          {step.kind !== 'guardrail' && <p className="text-caption1 font-semibold text-muted">{KIND_LABEL[step.kind]}</p>}
          <p className="text-label1 font-medium text-ink">{step.label}</p>
          <p className="text-body2 text-muted">{step.detail}</p>
        </li>
      ))}
    </ol>
  );
}
