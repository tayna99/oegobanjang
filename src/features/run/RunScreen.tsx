import { Button } from '@/components/Button';
import { OfflineBanner } from '@/components/OfflineBanner';
import type { RunConfig, RunStep } from '@/mocks/runs';
import { StepTimeline } from './StepTimeline';

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
    }
  | { status: 'error'; reason: 'out_of_scope' | 'blocked' | 'unknown'; message: string }
  | { status: 'offline'; lastSyncedAt: string };

export interface RunScreenProps {
  state: RunViewState;
  onApprove?: () => void;
  onAlt?: () => void;
}

// 1단계 스펙 §M9 5상태. approvalStore 연동(승인 결정 영속화)은 1.6 몫 — 여기서는
// UI/엔진 계약만 다룬다(docs/superpowers/specs/2026-07-06-run-engine-steptimeline-design.md).
export function RunScreen({ state, onApprove, onAlt }: RunScreenProps) {
  if (state.status === 'loading') {
    return <div className="p-5 text-sm text-muted">분석 중…</div>;
  }

  if (state.status === 'offline') {
    return (
      <div>
        <OfflineBanner lastSyncedAt={state.lastSyncedAt} />
        <div className="p-5 text-sm text-muted">오프라인 상태에서는 승인을 진행할 수 없습니다.</div>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="p-5">
        <p className="text-sm text-critical-text">{state.message}</p>
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
      <h2 className="mb-3 text-lg font-semibold text-ink">{state.title}</h2>
      <StepTimeline steps={state.steps} />
      {!state.readOnly && (
        <>
          <p className="mb-1 mt-4 text-sm text-ink">{state.question}</p>
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
