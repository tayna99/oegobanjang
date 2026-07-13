import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { BriefingScreen } from './BriefingScreen';
import type { CaseCard, Role } from '@/types';

const HEADER = { companyName: '그린푸드 제조', date: '7월 10일 (금)', unreadNotifications: 0 };

const CARD: CaseCard = {
  caseId: 'nguyen',
  caseCode: 'case_002',
  title: '체류기간 연장 서류 요청',
  workerRef: { displayName: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', maskLevel: 'masked' },
  severity: 'HIGH',
  dDay: 30,
  missingDocCount: 2,
  agentStage: 'awaiting_approval',
  state: 'approval_pending',
  approvalRequired: true,
  primaryAction: { actionId: 'a', label: '승인하기', state: 'ready', requiresApproval: true, kind: 'approve' },
  secondaryAction: { actionId: 'b', label: '초안 보기', state: 'ready', requiresApproval: false, kind: 'draft' },
  preparedBy: 'agent',
  preparedRunRef: '#4788',
};

const PROGRESS_CARD: CaseCard = {
  ...CARD,
  caseId: 'oyunaa',
  caseCode: 'case_006',
  title: '계약 만료 사전 모니터링',
  workerRef: { displayName: 'Oyunaa T.', nationality: '몽골', team: '포장팀', maskLevel: 'masked' },
  severity: 'LOW',
  dDay: 75,
  missingDocCount: undefined,
  agentStage: 'detected',
  state: 'draft',
  approvalRequired: false,
  preparedRunRef: undefined,
};

function renderScreen(state: Parameters<typeof BriefingScreen>[0]['state'], role: Role = 'manager') {
  return render(
    <MemoryRouter>
      <BriefingScreen state={state} header={HEADER} onOpenCase={vi.fn()} onSeeAllCases={vi.fn()} role={role} />
    </MemoryRouter>,
  );
}

// M2.6.1 재구성(Mobile §2a): 파이프라인 스탯 로우 + 승인 큐(단일 검토 CTA) +
// 에이전트 진행 중 리스트 + 고정 문구 + 커맨드바(존치). 상태 5종 유니온 유지.
describe('BriefingScreen — 상태 5종', () => {
  it('default: 파이프라인·승인 큐·진행 중 리스트·안전고지·커맨드바를 전부 렌더한다', () => {
    renderScreen({ status: 'default', cards: [CARD, PROGRESS_CARD] });
    expect(screen.getByLabelText('에이전트 파이프라인')).toBeInTheDocument();
    expect(screen.getByText('내가 처리할 승인 1건')).toBeInTheDocument();
    expect(screen.getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '검토' })).toBeInTheDocument();
    expect(screen.getByText('에이전트 진행 중 1건')).toBeInTheDocument();
    expect(screen.getByText(/Oyunaa T./)).toBeInTheDocument();
    expect(screen.getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('AI에게 요청하기')).toBeInTheDocument();
    // 승인 버튼은 카드에 없다 — 승인은 체크리스트(2c)에서만.
    expect(screen.queryByRole('button', { name: '승인하기' })).not.toBeInTheDocument();
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
    expect(screen.getByText(/그린푸드 제조/)).toBeInTheDocument();
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
    expect(screen.getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
  });

  it('offline: 경고형 오프라인 배너를 보여주고 검토 CTA를 비활성화한다', () => {
    renderScreen({ status: 'offline', cachedCards: [CARD], lastSyncedAt: '08:12' });
    expect(screen.getByText('오프라인 상태입니다 · 재연결 시 자동 동기화')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '검토' })).toBeDisabled();
  });
});

// 7단계 §6 M1 홈 역할 분기(운영급 RBAC 확장).
describe('BriefingScreen — 역할 분기', () => {
  it('owner: 파이프라인 통계는 숨기고 승인 관련 커맨드바 suggestion을 보여준다', () => {
    renderScreen({ status: 'default', cards: [CARD, PROGRESS_CARD] }, 'owner');
    expect(screen.queryByLabelText('에이전트 파이프라인')).not.toBeInTheDocument();
    expect(screen.getByText('오늘 승인 대기 요약해줘')).toBeInTheDocument();
  });

  it('viewer: CTA가 비활성화되고 커맨드바 자체가 없다', () => {
    renderScreen({ status: 'default', cards: [CARD, PROGRESS_CARD] }, 'viewer');
    expect(screen.getByRole('button', { name: '검토' })).toBeDisabled();
    expect(screen.getByRole('button', { name: PROGRESS_CARD.title })).toBeDisabled();
    expect(screen.queryByPlaceholderText('AI에게 요청하기')).not.toBeInTheDocument();
  });
});
