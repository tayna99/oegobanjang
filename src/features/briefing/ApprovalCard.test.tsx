import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ApprovalCard } from './ApprovalCard';
import type { CaseCard } from '@/types';

const CARD: CaseCard = {
  caseId: 'nguyen',
  caseCode: 'case_002',
  title: '체류기간 연장 서류 요청',
  workerRef: { displayName: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', maskLevel: 'masked' },
  severity: 'HIGH',
  dDay: 30,
  missingDocCount: 2,
  state: 'approval_pending',
  approvalRequired: true,
  primaryAction: { actionId: 'a', label: '승인하기', state: 'ready', requiresApproval: true, kind: 'approve' },
  secondaryAction: { actionId: 'b', label: '초안 보기', state: 'ready', requiresApproval: false, kind: 'draft' },
  preparedBy: 'agent',
  preparedRunRef: '#4788',
};

// M2.6.1 승인 큐 카드 계약(Mobile §2a): CTA는 "검토" 1개뿐 — 승인은 체크리스트(2c)에서만.
describe('ApprovalCard (승인 큐 카드)', () => {
  it('제목·근로자·심각도 칩·누락 칩을 렌더한다', () => {
    render(<ApprovalCard data={CARD} onReview={vi.fn()} />);
    expect(screen.getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
    expect(screen.getByText('Nguyen Van A · 제조1팀')).toBeInTheDocument();
    expect(screen.getByText('우선 확인 · D-30')).toBeInTheDocument();
    expect(screen.getByText('누락 2건')).toBeInTheDocument();
  });

  it('CTA는 "검토" 하나뿐이다 — 승인하기 버튼이 없다', () => {
    render(<ApprovalCard data={CARD} onReview={vi.fn()} />);
    expect(screen.getAllByRole('button')).toHaveLength(1);
    expect(screen.getByRole('button', { name: '검토' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '승인하기' })).not.toBeInTheDocument();
  });

  it('검토 클릭 시 onReview가 호출된다', () => {
    const onReview = vi.fn();
    render(<ApprovalCard data={CARD} onReview={onReview} />);
    screen.getByRole('button', { name: '검토' }).click();
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it('offlineDisabled면 검토 버튼이 비활성화된다', () => {
    render(<ApprovalCard data={CARD} onReview={vi.fn()} offlineDisabled />);
    expect(screen.getByRole('button', { name: '검토' })).toBeDisabled();
  });

  it('returned 상태면 반려 보완 칩을 보여준다', () => {
    render(<ApprovalCard data={{ ...CARD, state: 'returned' }} onReview={vi.fn()} />);
    expect(screen.getByText('반려됨 · 보완 필요')).toBeInTheDocument();
  });
});
