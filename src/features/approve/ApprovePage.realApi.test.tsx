import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// R2.4 — real API 모드에서 ApprovePage가 실제 승인/반려 엔드포인트를 호출하는지 검증한다.
// vi.mock은 파일 전체에 호이스트되어 apiFetch를 경유하는 모든 import가 동일하게 관측한다
// (StepPhoneAuth.realApi.test.tsx와 동일 관례).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', USE_REAL_API: true }));

import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';
import { useSessionStore } from '@/stores/sessionStore';
import type { CaseCard } from '@/types';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

// real 모드 케이스 id는 'cs_nguyen'처럼 CASE_SHEETS(mock, 'nguyen') 키와 다르다 —
// 선행 버그(CASE_SHEETS 조회 실패로 항상 "케이스를 찾을 수 없습니다") 재발 방지 회귀도 겸한다.
const REAL_CASE: CaseCard = {
  caseId: 'cs_nguyen',
  caseCode: 'case_002',
  title: '체류기간 연장 서류 요청',
  severity: 'HIGH',
  dDay: 10,
  state: 'approval_pending',
  approvalRequired: true,
  primaryAction: {
    actionId: 'act1',
    label: '승인하기',
    state: 'ready',
    requiresApproval: true,
    kind: 'approve',
    pendingApprovalId: 'apv1',
  },
  secondaryAction: { actionId: 'act1-confirm', label: '확인', state: 'ready', requiresApproval: false, kind: 'confirm' },
  preparedBy: 'agent',
};

describe('ApprovePage — real API 모드(R2.4)', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useCaseStore.getState().upsert(REAL_CASE);
    useRoleStore.getState().setRole('owner'); // owner_only 정책 분기를 피해 단순 happy-path만 본다.
    useCompanyStore.getState().reset();
  });

  afterEach(() => {
    useSessionStore.getState().clear();
    useRoleStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('기존 pendingApprovalId로 바로 승인 API를 호출하고 케이스 상태를 반영한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      approval: {
        id: 'apv1', company_id: 'cmp1', case_id: 'cs_nguyen', action_id: 'act1', status: 'approved',
        idempotency_key: 'k1', reason: null, requested_at: '2026-07-17T00:00:00Z',
        decided_at: '2026-07-17T01:00:00Z', decided_by_user_id: 'u_owner',
      },
      case_state: 'human_approved',
    }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/cs_nguyen/approve'] });
    render(<RouterProvider router={router} />);

    await screen.findByRole('heading', { name: '최종 승인' });
    // 체크리스트 전 항목 체크 — real 모드는 근거 개수를 지어내지 않으므로 일반 문구로 나온다.
    expect(screen.getByText('누락 서류·연결 근거 확인')).toBeInTheDocument();
    for (const box of screen.getAllByRole('checkbox').slice(0, 4)) fireEvent.click(box);

    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '1234' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/approvals/apv1/approve',
      expect.objectContaining({ method: 'POST' }),
    ));
    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).includes('/approve'))! as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body).toMatchObject({ identity_method: 'pin', pin: '1234' });

    await waitFor(() => expect(useCaseStore.getState().cases.cs_nguyen.state).toBe('human_approved'));
    await waitFor(() => expect(router.state.location.pathname).toBe('/case/cs_nguyen/history'));
  });

  it('승인 요청이 아직 없고 owner면 결정 경로가 없다는 에러를 보여준다', async () => {
    useCaseStore.getState().upsert({
      ...REAL_CASE,
      primaryAction: { ...REAL_CASE.primaryAction, pendingApprovalId: undefined },
    });
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/cs_nguyen/approve'] });
    render(<RouterProvider router={router} />);

    await screen.findByRole('heading', { name: '최종 승인' });
    for (const box of screen.getAllByRole('checkbox').slice(0, 4)) fireEvent.click(box);
    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '1234' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await waitFor(() => expect(screen.getByText('아직 생성된 승인 요청이 없습니다.')).toBeInTheDocument());
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('서버가 PIN 불일치(422)를 반환하면 에러 메시지를 보여준다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: 'PIN이 일치하지 않습니다' }, 422));
    global.fetch = fetchMock as unknown as typeof fetch;

    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/cs_nguyen/approve'] });
    render(<RouterProvider router={router} />);

    await screen.findByRole('heading', { name: '최종 승인' });
    for (const box of screen.getAllByRole('checkbox').slice(0, 4)) fireEvent.click(box);
    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '0000' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await waitFor(() => expect(screen.getByText('PIN이 일치하지 않습니다')).toBeInTheDocument());
    expect(useCaseStore.getState().cases.cs_nguyen.state).toBe('approval_pending');
  });
});
