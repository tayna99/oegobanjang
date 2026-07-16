import { fireEvent, render, screen, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useApprovalStore } from '@/stores/approvalStore';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

// 운영급 RBAC 확장 — 7단계 §2 각주1(승인 정책 분기)·§3.3(공동대표)·§6(M4 viewer 진입 불가).
describe('ApprovePage — 정책·공동대표·viewer 라우트 가드', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useApprovalStore.getState().reset();
    useEvidenceStore.getState().reset();
    useRoleStore.getState().reset();
    useCompanyStore.getState().reset();
  });

  function checkAllChecklist() {
    for (const box of within(screen.getByRole('list')).getAllByRole('checkbox')) {
      fireEvent.click(box);
    }
  }

  it('viewer는 최종 승인 화면에 진입할 수 없다', async () => {
    useRoleStore.getState().setRole('viewer');
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    expect(
      await screen.findByText('열람자 권한으로는 최종 승인 화면에 진입할 수 없습니다.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '최종 승인' })).not.toBeInTheDocument();
  });

  it('owner_only 정책이면 manager는 승인하기 대신 대표 승인 요청 버튼을 본다', async () => {
    useCompanyStore.getState().setApprovalPolicy('owner_only');
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '최종 승인' });
    checkAllChecklist();

    expect(screen.queryByRole('button', { name: '승인하기' })).not.toBeInTheDocument();
    const requestButton = screen.getByRole('button', { name: '대표 승인 요청' });
    expect(requestButton).toBeEnabled();

    fireEvent.click(requestButton);
    // 상태 전이는 없다 — 요청만 기록되고 홈으로 돌아간다.
    expect(useCaseStore.getState().cases.nguyen.state).toBe('approval_pending');
    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'approval_requested' && e.caseId === 'nguyen'),
    ).toBe(true);
    await screen.findByRole('region', { name: '승인 큐' });
  });

  it('owner_only 정책이어도 대리 승인 체크박스를 체크하면 승인하기로 되돌아온다', async () => {
    useCompanyStore.getState().setApprovalPolicy('owner_only');
    render(
      <RouterProvider
        router={createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] })}
      />,
    );
    await screen.findByRole('heading', { name: '최종 승인' });
    checkAllChecklist();
    expect(screen.getByRole('button', { name: '대표 승인 요청' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox', { name: /대리 승인으로 처리/ }));
    expect(screen.getByRole('button', { name: '승인하기' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '대표 승인 요청' })).not.toBeInTheDocument();
  });

  it('owner_only 정책이어도 owner 본인은 그대로 승인하기 버튼을 쓴다', async () => {
    useCompanyStore.getState().setApprovalPolicy('owner_only');
    useRoleStore.getState().setRole('owner');
    render(
      <RouterProvider
        router={createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] })}
      />,
    );
    await screen.findByRole('heading', { name: '최종 승인' });
    expect(screen.getByRole('button', { name: '승인하기' })).toBeInTheDocument();
  });

  it('이미 승인된 케이스를 다시 열면 결정자 배너를 보여주고 체크리스트는 없다', async () => {
    const nguyen = CASE_CARDS.find((c) => c.caseId === 'nguyen')!;
    useCaseStore.getState().upsert({ ...nguyen, state: 'human_approved' });
    useEvidenceStore.getState().append({
      id: 'seed-co-owner-decided',
      type: 'approval_decided',
      at: '2026-07-12T09:00:00.000Z',
      caseId: 'nguyen',
      actor: '대표 이대표 (본인 확인 완료)',
    });

    render(
      <RouterProvider
        router={createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] })}
      />,
    );

    expect(await screen.findByText('대표 이대표 (본인 확인 완료)이(가) 이미 결정했습니다')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '승인 체크리스트' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '판단 기록 보기' })).toBeInTheDocument();
  });
});
