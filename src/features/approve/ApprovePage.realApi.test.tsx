import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.4 — API_MODE를 'real'로 모듈 목(dataSeed.realApi.test.ts와 동일 관례). ApprovePage가
// GET /api/v1/cases/{id}(체크리스트·근거수·pending approval id)·GET /api/v1/delegations/mine·
// POST /api/v1/approvals/{id}/approve|reject를 실제로 호출하는지 fetch 레벨에서 검증한다.
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { ApprovePage } from './ApprovePage';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useRoleStore } from '@/stores/roleStore';
import type { CaseCard } from '@/types';

const CARD: CaseCard = {
  caseId: 'cs1',
  caseCode: 'case_001',
  title: '체류기간 연장 서류 요청',
  severity: 'HIGH',
  state: 'approval_pending',
  approvalRequired: true,
  primaryAction: { actionId: 'act1', label: '승인하기', state: 'ready', requiresApproval: true, kind: 'approve' },
  secondaryAction: { actionId: 'act1-detail', label: '상세', state: 'ready', requiresApproval: false, kind: 'detail' },
  preparedBy: 'rule',
};

const CASE_DETAIL_DTO = {
  id: 'cs1',
  case_code: 'case_001',
  title: '체류기간 연장 서류 요청',
  severity: 'HIGH',
  state: 'approval_pending',
  agent_stage: null,
  due_date: null,
  approval_required: true,
  prepared_by: 'rule',
  prepared_run_id: null,
  worker: null,
  primary_action: null,
  secondary_action: null,
  usable_citation_count: 2,
  guard_note: null,
  checked_items: [],
  next_wake: null,
  documents: [],
  pending_approval: {
    id: 'apv1',
    action_id: 'act1',
    checklist: [
      { key: 'risk', label: '위험도 검토', checked: false },
      { key: 'docs', label: '근거 확인', checked: false },
    ],
    requested_at: '2026-07-17T00:00:00Z',
  },
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(body === undefined ? undefined : JSON.stringify(body), { status });
}

function routeFetch(overrides: { onApprove?: () => Response; onReject?: () => Response } = {}) {
  return vi.fn((input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (url.endsWith('/api/v1/cases/cs1')) return Promise.resolve(jsonResponse(CASE_DETAIL_DTO));
    if (url.endsWith('/api/v1/delegations/mine')) return Promise.resolve(jsonResponse(null));
    if (url.endsWith('/api/v1/evidence') && method === 'GET') return Promise.resolve(jsonResponse([]));
    if (url.endsWith('/api/v1/evidence') && method === 'POST') return Promise.resolve(jsonResponse({}, 201));
    if (url.endsWith('/api/v1/approvals/apv1/approve')) {
      return Promise.resolve(overrides.onApprove ? overrides.onApprove() : jsonResponse({ approval: { id: 'apv1', status: 'approved' }, case_state: 'human_approved' }));
    }
    if (url.endsWith('/api/v1/approvals/apv1/reject')) {
      return Promise.resolve(overrides.onReject ? overrides.onReject() : jsonResponse({ approval: { id: 'apv1', status: 'rejected' }, case_state: 'returned' }));
    }
    throw new Error(`예상치 못한 fetch 호출: ${method} ${url}`);
  }) as unknown as typeof fetch;
}

function renderAt(path = '/case/cs1/approve') {
  useCaseStore.getState().upsert(CARD); // useSeedCases 실 GET을 우회(스토어가 이미 채워져 있으면 스킵)
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/case/:caseId/approve" element={<ApprovePage />} />
        <Route path="/case/:caseId/history" element={<div>승인 이력 화면</div>} />
        <Route path="/" element={<div>홈 화면</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ApprovePage — real 모드(R2.4)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useCaseStore.getState().reset();
    useEvidenceStore.getState().reset();
    useApprovalStore.getState().reset();
    useRoleStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('서버 상세로 체크리스트·근거수를 렌더하고, 전부 체크+PIN 승인 시 서버에 제출한다', async () => {
    const fetchMock = routeFetch();
    global.fetch = fetchMock;

    renderAt();

    await screen.findByRole('heading', { name: '최종 승인' });
    expect(await screen.findByText('위험도 검토')).toBeInTheDocument();
    expect(screen.getByText('근거 확인')).toBeInTheDocument();

    for (const box of within(screen.getByRole('list')).getAllByRole('checkbox')) fireEvent.click(box);
    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));

    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '1234' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/approvals/apv1/approve',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"checklist":[{"key":"risk","label":"위험도 검토","checked":true}'),
        }),
      ),
    );
    expect(await screen.findByText('승인 이력 화면')).toBeInTheDocument();
  });

  it('PIN이 서버에서 거부되면 에러 메시지를 표시하고 화면에 남는다', async () => {
    global.fetch = routeFetch({
      onApprove: () => jsonResponse({ detail: 'PIN이 일치하지 않습니다' }, 422),
    });

    renderAt();
    await screen.findByRole('heading', { name: '최종 승인' });
    for (const box of within(await screen.findByRole('list')).getAllByRole('checkbox')) fireEvent.click(box);
    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '9999' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    expect(await screen.findByText('PIN이 일치하지 않습니다')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '최종 승인' })).toBeInTheDocument();
  });

  it('반려 사유가 비어 있으면 real 모드에서 제출을 막는다', async () => {
    global.fetch = routeFetch();
    renderAt();

    await screen.findByRole('heading', { name: '최종 승인' });
    fireEvent.click(screen.getByRole('button', { name: '반려하기' }));

    expect(await screen.findByText('반려 사유를 입력해주세요.')).toBeInTheDocument();
    expect(screen.queryByText('본인확인 PIN')).not.toBeInTheDocument();
  });

  it('반려 사유 입력 + PIN 확인 시 서버에 반려를 제출한다', async () => {
    const fetchMock = routeFetch();
    global.fetch = fetchMock;
    renderAt();

    await screen.findByRole('heading', { name: '최종 승인' });
    fireEvent.change(screen.getByRole('textbox', { name: '의견 / 반려 사유' }), { target: { value: '서류 미비' } });
    fireEvent.click(screen.getByRole('button', { name: '반려하기' }));
    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '1234' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/approvals/apv1/reject',
        expect.objectContaining({ method: 'POST' }),
      ),
    );
    expect(await screen.findByText('홈 화면')).toBeInTheDocument();
  });

  it('대리 승인 체크박스는 유효한 위임이 있을 때만 보인다', async () => {
    global.fetch = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url.endsWith('/api/v1/cases/cs1')) return Promise.resolve(jsonResponse(CASE_DETAIL_DTO));
      if (url.endsWith('/api/v1/delegations/mine')) {
        return Promise.resolve(
          jsonResponse({ delegation_id: 'dlg1', delegator_user_id: 'usr_owner', delegator_name: '김대표', ends_at: '2027-01-01T00:00:00Z' }),
        );
      }
      if (url.endsWith('/api/v1/evidence') && method === 'GET') return Promise.resolve(jsonResponse([]));
      throw new Error(`예상치 못한 fetch 호출: ${method} ${url}`);
    }) as unknown as typeof fetch;
    useRoleStore.getState().setRole('manager');

    renderAt();

    await screen.findByRole('heading', { name: '최종 승인' });
    expect(await screen.findByText(/위임: 김대표/)).toBeInTheDocument();
  });

  it('위임이 없으면 대리 승인 체크박스를 보이지 않는다', async () => {
    global.fetch = routeFetch();
    useRoleStore.getState().setRole('manager');

    renderAt();

    await screen.findByRole('heading', { name: '최종 승인' });
    await screen.findByText('위험도 검토');
    expect(screen.queryByText(/대리 승인으로 처리/)).not.toBeInTheDocument();
  });
});
