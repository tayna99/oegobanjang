import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { OfflineBanner } from '@/components/OfflineBanner';
import { dDayLabel, dDayTone } from '@/lib/dday';
import type { RunConfig, RunStep } from '@/mocks/runs';
import { StepTimeline } from './StepTimeline';

// 3.2 커맨드 런 결과 카드 한 줄 — 런이 정리한 대상 케이스.
export interface RunResultCase {
  caseId: string;
  title: string;
  dDay?: number;
}

export type RunViewState =
  | { status: 'loading' }
  | {
      status: 'default';
      mode: RunConfig['mode'];
      title: string;
      question: string;
      altLabel: string;
      steps: RunStep[];
      engineStatus: 'streaming' | 'done';
      readOnly?: boolean;
      resultCases?: RunResultCase[];
    }
  | { status: 'error'; reason: 'out_of_scope' | 'blocked' | 'unknown'; message: string }
  | { status: 'offline'; lastSyncedAt: string };

export interface RunScreenProps {
  state: RunViewState;
  onApprove?: () => void;
  onAlt?: () => void;
  onOpenCase?: (caseId: string) => void;
}

// 1단계 스펙 §M9 5상태. approvalStore 연동(승인 결정 영속화)은 1.6 몫 — 여기서는
// UI/엔진 계약만 다룬다(docs/superpowers/specs/2026-07-06-run-engine-steptimeline-design.md).
export function RunScreen({ state, onApprove, onAlt, onOpenCase }: RunScreenProps) {
  if (state.status === 'loading') {
    return <div className="p-5 text-label1 text-muted">분석 중…</div>;
  }

  if (state.status === 'offline') {
    return (
      <div>
        <OfflineBanner lastSyncedAt={state.lastSyncedAt} />
        <div className="p-5 text-body2 text-muted">오프라인 상태에서는 승인을 진행할 수 없습니다.</div>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="p-5">
        <p className="text-body2 text-critical-text">{state.message}</p>
        {state.reason === 'out_of_scope' && (
          <Button variant="outline" className="mt-3" onClick={onAlt}>
            행정사 검토 요청
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="p-5">
      <h2 className="mb-3 text-heading2 font-semibold text-ink">{state.title}</h2>
      <StepTimeline steps={state.steps} streaming={state.engineStatus === 'streaming'} />
      {state.engineStatus === 'done' && state.resultCases && state.resultCases.length > 0 && (
        <section aria-label="처리 대상 케이스" className="mt-4">
          <h3 className="mb-2 text-label1 font-semibold text-subtle">
            처리 대상 케이스 {state.resultCases.length}건
          </h3>
          <ul className="flex flex-col gap-2">
            {state.resultCases.map((c) => (
              <li key={c.caseId}>
                <button
                  type="button"
                  onClick={() => onOpenCase?.(c.caseId)}
                  className="flex w-full items-center gap-2 rounded-xl bg-surface px-3.5 py-3 text-left shadow-outline transition-colors hover:bg-neutbg"
                >
                  {c.dDay !== undefined && <Chip tone={dDayTone(c.dDay)}>{dDayLabel(c.dDay)}</Chip>}
                  <span className="min-w-0 flex-1 truncate text-body2 text-ink">{c.title}</span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    className="shrink-0 text-faint"
                    aria-hidden="true"
                  >
                    <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {!state.readOnly && (
        <>
          <p className="mb-1 mt-4 text-body2 text-ink">{state.question}</p>
          <div className="mt-2 flex gap-2.5">
            <Button variant="outline" onClick={onAlt} className="flex-1">
              {state.altLabel}
            </Button>
            <Button
              variant="primary"
              disabled={state.engineStatus !== 'done'}
              onClick={onApprove}
              className="flex-1"
            >
              승인
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
