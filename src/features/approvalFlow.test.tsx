import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useApprovalStore } from '@/stores/approvalStore';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

// M2.6 승인 깔때기 E2E — "카드에서는 검토만, 승인은 체크리스트 화면에서"(블루프린트 §1).
// 2b 사례 검토 → 검토 계속 → 2c 체크리스트(필수 4/4 게이트) → 승인 → 2d 승인 이력 → 홈 상태 반영.
describe('M2.6 approval funnel', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useApprovalStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  it('검토 → 체크리스트 승인 → 이력까지 흐르고 홈 승인 큐에서 빠진다', async () => {
    const router = createMemoryRouter(routeConfig, {
      initialEntries: ['/case/nguyen'],
    });
    render(<RouterProvider router={router} />);

    // 2b 사례 검토 — 초안 미리보기 인라인(언어 토글), 승인 버튼 없음.
    await screen.findByRole('heading', { name: '사례 검토' });
    expect(screen.getByText(/Xin chào Nguyen/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '한국어' }));
    expect(screen.getByText(/안녕하세요 Nguyen 씨/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '승인하기' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '검토 계속' }));

    // 2c 최종 승인 — 체크리스트 4/4 전에는 승인 불가(성급한 승인 방지 게이트).
    await screen.findByRole('heading', { name: '최종 승인' });
    expect(screen.getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();
    const approveButton = screen.getByRole('button', { name: '승인하기' });
    expect(approveButton).toBeDisabled();

    for (const box of screen.getAllByRole('checkbox')) {
      fireEvent.click(box);
    }
    expect(screen.getByText('필수 4/4')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '승인하기' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));

    // 2d 승인 이력 — 사람 결정 노드(최종 승인)와 판단 기록.
    await screen.findByRole('heading', { name: '승인 이력' });
    expect(screen.getByText(/승인 완료 · 판단 기록/)).toBeInTheDocument();
    expect(screen.getByText('최종 승인')).toBeInTheDocument();
    expect(screen.getByText('발송 실행 (mock)')).toBeInTheDocument();
    expect(screen.getByText('모든 판단·승인은 Evidence Log에 기록됩니다.')).toBeInTheDocument();

    // 홈으로 — 승인된 케이스는 승인 큐에서 빠진다(2건 남음).
    fireEvent.click(screen.getByRole('button', { name: '뒤로' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(screen.getByText('내가 처리할 승인 2건')).toBeInTheDocument();

    expect(useCaseStore.getState().cases.nguyen.state).toBe('human_approved');
    expect(useApprovalStore.getState().approvals['nguyen-approve'].status).toBe('approved');
    const types = useEvidenceStore.getState().events.map((event) => event.type);
    expect(types).toContain('review_started');
    expect(types).toContain('checklist_completed');
    expect(types).toContain('approval_decided');
  });

  it('반려하기는 사유와 함께 returned 상태로 되돌리고 큐에 보완 칩이 남는다', async () => {
    const router = createMemoryRouter(routeConfig, {
      initialEntries: ['/case/nguyen/approve'],
    });
    render(<RouterProvider router={router} />);

    await screen.findByRole('heading', { name: '최종 승인' });
    fireEvent.change(screen.getByRole('textbox', { name: '의견 / 반려 사유' }), {
      target: { value: '초안 톤 수정 필요' },
    });
    fireEvent.click(screen.getByRole('button', { name: '반려하기' }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(useCaseStore.getState().cases.nguyen.state).toBe('returned');
    expect(useApprovalStore.getState().approvals['nguyen-approve'].status).toBe('rejected');
    expect(useApprovalStore.getState().approvals['nguyen-approve'].reason).toBe('초안 톤 수정 필요');
    expect(screen.getByText('반려됨 · 보완 필요')).toBeInTheDocument();
  });
});
