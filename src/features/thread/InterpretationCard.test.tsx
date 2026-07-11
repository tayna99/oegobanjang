import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Interpretation } from '@/types';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { InterpretationCard } from './InterpretationCard';
import type { InterpretationCardProps } from './InterpretationCard';

const INTERPRETATION: Interpretation = {
  interpretationId: 'tran-interp-1',
  threadId: 'tran',
  caseId: 'tranCase',
  summaryKo: '표준근로계약서는 회사가 보관 중이라고 답했습니다.',
  confidence: 'high',
  updates: [
    { field: '표준근로계약서', from: '누락', to: '회사 확인 필요', badgeTone: 'warning' },
    { field: '여권 사본', from: '누락', to: '제출 예정 · 내일', badgeTone: 'warning' },
  ],
  recommendedActions: [
    {
      action: {
        actionId: 'tranCase-interp-confirm-contract',
        label: '회사 보관 계약서 확인',
        state: 'ready',
        requiresApproval: false,
        kind: 'confirm',
      },
      reason: '표준근로계약서를 회사가 보관 중이라고 응답했습니다',
    },
  ],
  isFinal: false,
  confirmedSummary: 'Tran 응답 해석 확인 — 서류 상태 2건 갱신',
  confirmedCardText: '상태 반영 완료 — 계약서 회사 확인 · 여권 제출 대기 (판단 기록 #4791)',
  evidenceRef: '#4791',
};

// useNextAction()(→useNavigate())을 항상 호출하므로 Router 컨텍스트가 필요하다.
function renderCard(props: InterpretationCardProps) {
  return render(
    <MemoryRouter>
      <InterpretationCard {...props} />
    </MemoryRouter>,
  );
}

describe('InterpretationCard', () => {
  beforeEach(() => {
    useEvidenceStore.getState().reset();
  });

  it('헤더 배지·요약·갱신 목록·추천 액션을 렌더한다', () => {
    renderCard({ interpretation: INTERPRETATION, onConfirm: vi.fn() });

    expect(screen.getByText('담당자 확인 필요')).toBeInTheDocument();
    expect(screen.getByText(INTERPRETATION.summaryKo)).toBeInTheDocument();
    expect(screen.getByText('표준근로계약서')).toBeInTheDocument();
    expect(screen.getByText('여권 사본')).toBeInTheDocument();
    expect(screen.getByText('회사 보관 계약서 확인')).toBeInTheDocument();
  });

  it('confidence:low면 경고 문구를 추가로 보여준다', () => {
    renderCard({ interpretation: { ...INTERPRETATION, confidence: 'low' }, onConfirm: vi.fn() });
    expect(screen.getByText('해석이 불확실합니다. 원문을 확인해주세요')).toBeInTheDocument();
  });

  it('[상태 반영 확인] 클릭 시 모든 updates의 field를 updateIds로 onConfirm을 호출한다', () => {
    const onConfirm = vi.fn();
    renderCard({ interpretation: INTERPRETATION, onConfirm });

    fireEvent.click(screen.getByRole('button', { name: '상태 반영 확인' }));
    expect(onConfirm).toHaveBeenCalledWith(['표준근로계약서', '여권 사본']);
  });

  it('confirmDisabled면 확인 버튼이 비활성화된다(오프라인)', () => {
    renderCard({ interpretation: INTERPRETATION, onConfirm: vi.fn(), confirmDisabled: true });
    expect(screen.getByRole('button', { name: '상태 반영 확인' })).toBeDisabled();
  });

  it('추천 액션 클릭 시 useNextAction의 confirm 경로로 evidence가 기록된다(발송 없음)', () => {
    renderCard({ interpretation: INTERPRETATION, onConfirm: vi.fn() });

    fireEvent.click(screen.getByRole('button', { name: /회사 보관 계약서 확인/ }));
    const events = useEvidenceStore.getState().events;
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('approval_decided');
    expect(events[0].caseId).toBe('tranCase');
  });
});
