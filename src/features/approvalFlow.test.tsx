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
    // 홈 컨테이너(HomePage)가 useIsDesktop 분기 후 BriefingScreen을 커밋하므로 DOM 기준으로 대기.
    fireEvent.click(screen.getByRole('button', { name: '뒤로' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    await screen.findByText('내가 처리할 승인 2건', undefined, { timeout: 5000 });

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

  // 코드리뷰 A3 회귀: 반려는 감사 이력에서 '반려'로 표기되고 '최종 승인'(사람 primary 노드)이 아니다.
  it('반려한 케이스의 이력은 최종 승인이 아니라 반려로 기록된다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '최종 승인' });
    fireEvent.click(screen.getByRole('button', { name: '반려하기' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));

    // 이력 화면 진입 — 승인 노드/배너가 없어야 한다.
    router.navigate('/case/nguyen/history');
    await screen.findByRole('heading', { name: '승인 이력' });
    expect(screen.getAllByText('반려').length).toBeGreaterThan(0);
    expect(screen.queryByText('최종 승인')).not.toBeInTheDocument();
    expect(screen.queryByText(/승인 완료 · 판단 기록/)).not.toBeInTheDocument();
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'approval_rejected')).toBe(true);
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'approval_decided')).toBe(false);
  });

  // 코드리뷰 A1/B2 회귀: 반려 → 재검토(재개) → 재승인이 크래시 없이 완료된다.
  it('반려된 케이스를 다시 검토하면 승인 대기로 열리고 재승인이 성공한다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '최종 승인' });
    fireEvent.click(screen.getByRole('button', { name: '반려하기' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(useCaseStore.getState().cases.nguyen.state).toBe('returned');

    // 재검토: 반려 카드 → 검토(2b) → 검토 계속(재개: returned→approval_pending) → 재승인.
    router.navigate('/case/nguyen');
    await screen.findByRole('heading', { name: '사례 검토' });
    fireEvent.click(screen.getByRole('button', { name: '검토 계속' }));
    await screen.findByRole('heading', { name: '최종 승인' });
    expect(useCaseStore.getState().cases.nguyen.state).toBe('approval_pending'); // 재개됨

    for (const box of screen.getAllByRole('checkbox')) fireEvent.click(box);
    fireEvent.click(screen.getByRole('button', { name: '승인하기' })); // 크래시 없이 성공
    await screen.findByRole('heading', { name: '승인 이력' });
    expect(useCaseStore.getState().cases.nguyen.state).toBe('human_approved');
  });

  // 코드리뷰 A2/B3/F3 회귀: 고위험 blocked 케이스는 앱에서 승인 불가(전달 전용).
  it('고위험(기한 경과) 케이스는 검토 계속 대신 행정사 전달 준비만, 승인 화면에서도 승인 불가', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/batbayar'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '사례 검토' });
    // 앱 승인 경로(검토 계속)가 없고, 행정사 전달 준비 안내만.
    expect(screen.queryByRole('button', { name: '검토 계속' })).not.toBeInTheDocument();
    expect(screen.getByText('행정사 전달 준비 (승인 후)')).toBeInTheDocument();

    // 승인 화면에 직접 진입해도 승인하기는 비활성 + 앱 승인 불가 안내.
    router.navigate('/case/batbayar/approve');
    await screen.findByRole('heading', { name: '최종 승인' });
    expect(screen.getByText('이 케이스는 앱에서 승인할 수 없습니다')).toBeInTheDocument();
    for (const box of screen.getAllByRole('checkbox')) fireEvent.click(box);
    expect(screen.getByRole('button', { name: '승인하기' })).toBeDisabled();
  });
});
