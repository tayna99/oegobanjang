import { useEffect, useRef, useState } from 'react';
import { Card } from '@/components/Card';
import { Chip } from '@/components/Chip';
import { IconLock } from '@/components/icons';
import { dDayLabel } from '@/lib/dday';
import { severityLabel, severityTone } from '@/lib/chipTone';
import { StepTimeline } from '@/features/run/StepTimeline';
import { CASE_CARDS } from '@/mocks/fixtures';
import type { RunStep } from '@/mocks/runs';

// O5 — 첫 브리핑 동기 생성(Aha). 로딩은 각본 기반 3스텝(RunEngine 각본 철학과 동일, 실제
// LLM 연결 없음) — StepTimeline(런 재생 화면과 동일 컴포넌트)을 그대로 재사용해 새 진행률
// UI를 발명하지 않는다. 완료 카드 미리보기는 이미 시드돼 있는 nguyen 케이스(case_002)를
// 그대로 보여준다 — "always-non-empty"(3단계 O5)를 새 데이터 없이 만족한다.
const LOAD_STEPS: RunStep[] = [
  { kind: 'thinking', label: '감지', detail: '체류·계약·서류 이벤트를 확인했습니다' },
  { kind: 'tool_call', label: '근거 수집', detail: '관련 법령·내부 근거를 연결했습니다' },
  { kind: 'tool_call', label: '초안', detail: '확인용 메시지 초안을 준비했습니다' },
];

const PHASE_DURATION_MS = 900;

export interface StepBriefingLoadingProps {
  onComplete: () => void;
}

export function StepBriefingLoading({ onComplete }: StepBriefingLoadingProps) {
  const [phase, setPhase] = useState(0);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), PHASE_DURATION_MS);
    const t2 = setTimeout(() => setPhase(2), PHASE_DURATION_MS * 2);
    const t3 = setTimeout(() => onCompleteRef.current(), PHASE_DURATION_MS * 3);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  return (
    <div className="flex flex-col gap-6 pt-2">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-heading1 font-bold text-ink">첫 브리핑을 준비하고 있어요</h1>
        <p className="text-body2 text-muted">6명의 체류 · 계약 · 서류를 확인하는 중</p>
      </div>
      <div className="rounded-card bg-canvas p-4 shadow-outline-strong">
        <StepTimeline steps={LOAD_STEPS.slice(0, phase + 1)} streaming />
      </div>
      <div className="flex items-center justify-center gap-1.5">
        <IconLock width={12} height={12} className="text-subtle" />
        <span className="text-caption1 text-muted">확인한 뒤 승인 단계에서 진행합니다</span>
      </div>
    </div>
  );
}

export function StepBriefingDone() {
  // nguyen(case_002) — 이미 시드돼 있는 데모 세계관 케이스를 그대로 미리보기한다.
  const previewCard = CASE_CARDS.find((card) => card.caseId === 'nguyen')!;

  return (
    <div className="flex flex-col gap-5 pt-2">
      <div className="flex flex-col gap-2.5">
        <span className="flex size-11 items-center justify-center rounded-full bg-succbg">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M6 12.5L10.5 17L18 7.5" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" className="text-success" />
          </svg>
        </span>
        <div className="flex flex-col gap-1">
          <h1 className="text-heading1 font-bold text-ink">첫 브리핑이 준비됐어요</h1>
          <p className="text-body2 text-muted">오늘 확인할 항목을 정리했어요</p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <span className="px-0.5 text-caption1 font-semibold text-subtle">가장 먼저 볼 카드</span>
        <Card className="flex flex-col gap-3 p-4">
          <div className="flex flex-col gap-0.5">
            <h3 className="text-body1 font-semibold text-ink">{previewCard.title}</h3>
            <p className="text-caption1 text-subtle">
              {previewCard.workerRef?.displayName} · {previewCard.workerRef?.team}
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Chip tone={severityTone(previewCard.severity)}>
              {severityLabel(previewCard.severity)} · {dDayLabel(previewCard.dDay ?? 0)}
            </Chip>
            {previewCard.approvalRequired && <Chip tone="approval">승인 필요</Chip>}
          </div>
          <div className="flex items-center gap-2 rounded-in bg-surface px-3 py-2.5">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M5 12.5L10 17.5L19 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-primary" />
            </svg>
            <span className="text-label1 text-ink">다음 안전한 행동은 서류 요청 검토입니다</span>
          </div>
        </Card>
      </div>

      <p className="text-center text-caption1 text-muted">승인 전에는 외부 발송이 차단됩니다</p>
    </div>
  );
}
