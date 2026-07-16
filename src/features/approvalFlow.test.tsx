import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useApprovalStore } from '@/stores/approvalStore';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

describe('M1~M5 approval happy path', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useApprovalStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  it('moves from case deep link to draft, approval, done, and reflects approved state on M1', async () => {
    const router = createMemoryRouter(routeConfig, {
      initialEntries: ['/case/nguyen'],
    });
    render(<RouterProvider router={router} />);

    await screen.findByText('표준근로계약서 사본');
    fireEvent.click(screen.getAllByRole('button', { name: '초안 보기' }).at(-1)!);

    await screen.findByRole('heading', { name: '서류 요청 메시지' });
    fireEvent.click(screen.getByRole('button', { name: '베트남어' }));
    expect(screen.getByText(/Xin chào Nguyen/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '수정 요청' }));
    await screen.findByText('수정 요청 시트');
    fireEvent.click(screen.getByRole('button', { name: '부드럽게 다듬기' }));
    expect(screen.getByText(/잘 지내고 계신가요/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '승인 검토로 이동' }));
    await screen.findByText('승인 전 확인');

    expect(screen.getByRole('button', { name: '승인' })).toBeDisabled();
    await waitFor(() => expect(screen.getByRole('button', { name: '승인' })).toBeEnabled(), { timeout: 2000 });

    fireEvent.click(screen.getByRole('button', { name: '승인' }));
    await screen.findByRole('heading', { name: '발송 승인 완료' });
    expect(screen.getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '오늘 브리핑으로' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));

    const nguyenCard = screen.getByText('체류기간 연장 서류 요청').closest('[data-case-id="nguyen"]');
    expect(nguyenCard).not.toBeNull();
    expect(within(nguyenCard as HTMLElement).getByText('승인 완료')).toBeInTheDocument();

    expect(useCaseStore.getState().cases.nguyen.state).toBe('human_approved');
    expect(useApprovalStore.getState().approvals['nguyen-approve'].status).toBe('approved');
    expect(useEvidenceStore.getState().events.some((event) => event.type === 'approval_decided')).toBe(true);
  }, 10_000);
});
