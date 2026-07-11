import type { RunStep } from '@/mocks/runs';
import { Chip } from '@/components/Chip';
import { cn } from '@/lib/cn';

export interface StepTimelineProps {
  steps: RunStep[];
  /** true면 마지막 스텝이 진행 중(파랑 펄스 링) — RunScreen engineStatus 연동(2.5.4b). */
  streaming?: boolean;
}

const KIND_LABEL: Record<RunStep['kind'], string> = {
  thinking: '판단',
  tool_call: '도구 실행',
  guardrail: '가드레일',
  handoff: '핸드오프',
  replan: '재계획',
};

// StepTimeline — Montage 공용 컴포넌트.dc.html §6 세로형(2.5.4b 재설계):
// done=초록 체크 원, active=파랑 펄스 링(step-ring-pulse), 커넥터 라인.
// GOTCHAS: "가드레일은 숨기지 않고 스텝으로 노출 — 신뢰 자산" — 가드레일 스텝은
// 경고 톤 칩·라벨 색으로 다른 스텝과 시각 구분한다(스펙 M9 kind 어휘 유지).
export function StepTimeline({ steps, streaming = false }: StepTimelineProps) {
  return (
    <ol className="flex flex-col">
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        const isActive = streaming && isLast;
        const isGuardrail = step.kind === 'guardrail';
        return (
          <li key={index} className="flex gap-3">
            <span className="flex w-5 shrink-0 flex-col items-center" aria-hidden="true">
              <span
                className={cn(
                  'flex size-5 shrink-0 items-center justify-center rounded-full',
                  isActive
                    ? 'step-ring-pulse bg-primary'
                    : isGuardrail
                      ? 'bg-warnbg shadow-outline-strong'
                      : 'bg-success',
                )}
              >
                {!isActive && !isGuardrail && (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                    <path d="M5 12.5L10 17.5L19 7" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
                {isGuardrail && !isActive && (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="text-warning">
                    <path d="M12 3l9 16H3l9-16z" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
                  </svg>
                )}
              </span>
              {!isLast && <span className="min-h-5 w-0.5 flex-1 bg-neutbg" />}
            </span>
            <span className={cn('flex min-w-0 flex-col gap-0.5', !isLast && 'pb-4')}>
              <span className="flex items-center gap-1.5">
                <Chip tone={isGuardrail ? 'high' : 'neutral'}>{KIND_LABEL[step.kind]}</Chip>
                <span className={cn('text-label1 font-semibold', isGuardrail ? 'text-warning' : 'text-ink')}>
                  {step.label}
                </span>
              </span>
              <span className="text-pc-sm leading-snug text-subtle">{step.detail}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
