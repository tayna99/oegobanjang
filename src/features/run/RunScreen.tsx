import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { OfflineBanner } from '@/components/OfflineBanner';
import { SafetyNoticeEmphasis } from '@/components/SafetyNotice';
import { dDayLabel, dDayTone } from '@/lib/dday';
import type { RunConfig, RunStep } from '@/mocks/runs';
import { StepTimeline } from './StepTimeline';

// R4.1 — 라이브 QA 런(Tier1)의 최종 답변. 케이스 연결이 없는 순수 정보 응답이라
// RunResultCase(케이스 카드)가 아니라 텍스트+근거로 표시한다.
export interface RunAnswerView {
  text: string;
  citations: { sourceId: string; title: string; grade: string }[];
  missingEvidence: boolean;
  // structured.approval.required=true일 때만 채움 — 액션 버튼은 만들지 않는다(승인할 케이스/
  // 초안이 없는 순수 QA), 침묵하지 않고 정보로만 알린다(AGENTS.md §8).
  approvalNotice?: string;
}

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
      // replay 전용이 원래 의미이나(mocks/runs.ts RunConfig.readOnly), R4.1부터 라이브 QA
      // 런(mode:'command', 케이스·초안 없이 답변만 보여줌 — 승인할 대상 자체가 없음)도
      // readOnly:true로 넘겨 승인/대안 버튼 블록을 동일하게 숨기는 데 재사용한다.
      readOnly?: boolean;
      resultCases?: RunResultCase[];
      answer?: RunAnswerView;
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
      {state.engineStatus === 'done' && state.answer && (
        <section aria-label="답변" className="mt-4">
          <p className="text-body2 text-ink">{state.answer.text}</p>
          {state.answer.missingEvidence && (
            <p className="mt-2 text-label1 text-muted">근거를 찾지 못했습니다 — 행정사 검토가 필요합니다.</p>
          )}
          {state.answer.citations.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {state.answer.citations.map((c) => (
                <li key={c.sourceId}>
                  <Chip tone="neutral">
                    {c.grade}등급 · {c.title}
                  </Chip>
                </li>
              ))}
            </ul>
          )}
          {state.answer.approvalNotice && (
            <div className="mt-3">
              <SafetyNoticeEmphasis>{state.answer.approvalNotice}</SafetyNoticeEmphasis>
            </div>
          )}
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
