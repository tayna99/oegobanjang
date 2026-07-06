import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { BriefingScreen } from './BriefingScreen';
import type { CaseCard } from '@/types';

const HEADER = { companyName: '화성1공장', date: '2026.07.06', unreadNotifications: 0 };

const CARD: CaseCard = {
  caseId: 'nguyen',
  title: 'Nguyen V. 체류기간 연장 서류 요청',
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

function renderScreen(state: Parameters<typeof BriefingScreen>[0]['state']) {
  return render(
    <MemoryRouter>
      <BriefingScreen state={state} header={HEADER} onOpenCase={vi.fn()} onSeeAllCases={vi.fn()} />
    </MemoryRouter>,
  );
}

describe('BriefingScreen — 상태 5종', () => {
  it('default: 카드·통계·안전고지·커맨드바를 전부 렌더한다', () => {
    renderScreen({ status: 'default', cards: [CARD], stats: [] });
    expect(screen.getByText('Nguyen V. 체류기간 연장 서류 요청')).toBeInTheDocument();
    expect(screen.getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('AI에게 요청하기')).toBeInTheDocument();
  });

  it('empty(근로자 있음): 완료 문구 + 케이스 전체 보기 버튼을 보여준다', () => {
    renderScreen({ status: 'empty', hasWorkers: true, nextScheduledHint: '다음: 7/12 Tran 계약종료 D-30 진입 예정' });
    expect(screen.getByText('오늘 승인할 업무가 없습니다.')).toBeInTheDocument();
    expect(screen.getByText(/7\/12 Tran 계약종료/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '케이스 전체 보기' })).toBeInTheDocument();
  });

  it('empty(근로자 0명): 온보딩 유도 문구 + 근로자 등록 버튼을 보여준다(DoD)', () => {
    renderScreen({ status: 'empty', hasWorkers: false });
    expect(screen.getByText('근로자를 등록하면 매일 브리핑이 시작됩니다')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '근로자 등록' })).toBeInTheDocument();
  });

  it('loading: 헤더는 즉시 렌더되고 카드 자리는 스켈레톤이며 수치가 없다', () => {
    renderScreen({ status: 'loading' });
    expect(screen.getByText('화성1공장')).toBeInTheDocument();
    expect(screen.queryByText(/D-\d/)).not.toBeInTheDocument();
  });

  it('error: 실패 문구와 다시 시도 버튼을 보여준다', () => {
    renderScreen({ status: 'error', hasCachedData: false });
    expect(screen.getByText('브리핑을 불러오지 못했습니다')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument();
  });

  it('error(캐시 있음): 캐시된 카드 + 어제 데이터 배너를 보여준다', () => {
    renderScreen({ status: 'error', hasCachedData: true, cachedCards: [CARD] });
    expect(screen.getByText('어제 데이터입니다')).toBeInTheDocument();
    expect(screen.getByText('Nguyen V. 체류기간 연장 서류 요청')).toBeInTheDocument();
  });

  it('offline: 오프라인 배너를 보여주고 승인 CTA를 비활성화한다', () => {
    renderScreen({ status: 'offline', cachedCards: [CARD], lastSyncedAt: '08:12' });
    expect(screen.getByText(/오프라인/)).toBeInTheDocument();
    expect(screen.getByText('08:12')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '승인하기' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '초안 보기' })).not.toBeDisabled();
  });
});
