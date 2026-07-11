import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApprovalCard } from './ApprovalCard';
import type { CaseCard } from '@/types';

const NGUYEN: CaseCard = {
  caseId: 'nguyen',
  caseCode: 'case_002',
  title: 'Nguyen V. 체류기간 연장 서류 요청',
  severity: 'HIGH',
  dDay: 30,
  missingDocCount: 2,
  state: 'approval_pending',
  approvalRequired: true,
  primaryAction: { actionId: 'nguyen-approve', label: '승인하기', state: 'ready', requiresApproval: true, kind: 'approve' },
  secondaryAction: { actionId: 'nguyen-draft', label: '초안 보기', state: 'ready', requiresApproval: false, kind: 'draft' },
  preparedBy: 'agent',
  preparedRunRef: '#4788',
};

function renderCard(overrides: Partial<CaseCard> = {}, layout: 'hero' | 'compact' = 'hero') {
  const onOpen = vi.fn();
  render(
    <MemoryRouter>
      <ApprovalCard data={{ ...NGUYEN, ...overrides }} layout={layout} onOpen={onOpen} recommendReason={layout === 'hero' ? 'D-30이고 누락 서류 2건이 있어 오늘 요청이 필요합니다' : undefined} />
    </MemoryRouter>,
  );
  return { onOpen };
}

describe('ApprovalCard', () => {
  it('제목과 배지(D-day, 누락 N건, 승인 필요, severity)를 렌더한다', () => {
    renderCard();
    expect(screen.getByText('Nguyen V. 체류기간 연장 서류 요청')).toBeInTheDocument();
    expect(screen.getByText('D-30')).toBeInTheDocument();
    expect(screen.getByText('누락 2건')).toBeInTheDocument();
    expect(screen.getByText('승인 필요')).toBeInTheDocument();
  });

  it('CTA는 정확히 2개다', () => {
    renderCard();
    expect(screen.getAllByRole('button').filter((b) => ['승인하기', '초안 보기'].includes(b.textContent ?? ''))).toHaveLength(2);
  });

  it('hero 레이아웃에서만 추천 이유를 보여준다', () => {
    renderCard({}, 'hero');
    expect(screen.getByText(/D-30이고 누락 서류 2건이 있어/)).toBeInTheDocument();
  });

  it('compact 레이아웃에서는 추천 이유를 보여주지 않는다', () => {
    renderCard({}, 'compact');
    expect(screen.queryByText(/D-30이고 누락 서류 2건이 있어/)).not.toBeInTheDocument();
  });

  it('compact 레이아웃에서는 primary CTA도 secondary(비파랑) 색으로 렌더한다(화면당 파랑 CTA 1개)', () => {
    renderCard({}, 'compact');
    const primaryBtn = screen.getByText('승인하기');
    expect(primaryBtn).not.toHaveClass('bg-primary');
    expect(primaryBtn).toHaveClass('bg-surface');
  });

  it('preparedBy가 agent면 프로액티브 행을 보여준다', () => {
    renderCard({ preparedBy: 'agent', preparedRunRef: '#4788' });
    expect(screen.getByText(/AI가 준비를 마쳤습니다/)).toBeInTheDocument();
  });

  it('preparedBy가 rule이면 프로액티브 행을 보여주지 않는다', () => {
    renderCard({ preparedBy: 'rule', preparedRunRef: undefined });
    expect(screen.queryByText(/AI가 준비를 마쳤습니다/)).not.toBeInTheDocument();
  });

  it('카드 본문을 탭하면 onOpen이 실행된다(CTA 영역 제외)', () => {
    const { onOpen } = renderCard();
    fireEvent.click(screen.getByText('Nguyen V. 체류기간 연장 서류 요청'));
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it('CTA를 탭해도 onOpen은 실행되지 않는다(stopPropagation)', () => {
    const { onOpen } = renderCard();
    fireEvent.click(screen.getByText('초안 보기'));
    expect(onOpen).not.toHaveBeenCalled();
  });

  it('프로액티브 행을 탭하면 preparedRunRef의 재생 화면으로 이동한다(# 제거 후 이동)', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={<ApprovalCard data={NGUYEN} layout="hero" onOpen={vi.fn()} />}
          />
          <Route path="/run/:runId" element={<div>런 재생 화면</div>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText(/AI가 준비를 마쳤습니다/));
    expect(screen.getByText('런 재생 화면')).toBeInTheDocument();
  });
});
