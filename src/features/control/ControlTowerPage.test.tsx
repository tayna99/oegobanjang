import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';

function mockViewport(desktop: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: desktop,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

function renderAt(path: string) {
  useCaseStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
});

describe('ControlTowerPage (PC §3a, 2.5.6 DoD)', () => {
  beforeEach(() => mockViewport(true));

  it('데스크톱 "/"는 컨트롤 타워를 렌더한다 (파이프라인·KPI·우선 처리 큐)', () => {
    renderAt('/');
    const tower = screen.getByRole('region', { name: '컨트롤 타워' });
    expect(within(tower).getByRole('heading', { name: '컨트롤 타워' })).toBeInTheDocument();
    const pipeline = within(tower).getByLabelText('에이전트 파이프라인');
    expect(within(tower).getByLabelText('우선 처리 케이스')).toBeInTheDocument();
    // 파이프라인 누적 깔때기 라벨 (같은 어휘가 큐 단계 칩에도 나오므로 파이프라인으로 스코프).
    expect(within(pipeline).getByText('감지됨')).toBeInTheDocument();
    expect(within(pipeline).getByText('승인 대기')).toBeInTheDocument();
    // 고정 문구.
    expect(within(tower).getByText(/승인 전에는 외부 발송이 차단됩니다/)).toBeInTheDocument();
  });

  it('우선 처리 큐가 위험도×D-day로 정렬된다 — 첫 행 = 즉시 확인 batbayar', () => {
    renderAt('/');
    const queue = screen.getByLabelText('우선 처리 케이스');
    const rows = within(queue).getAllByRole('listitem');
    expect(within(rows[0]).getByText('Batbayar E.')).toBeInTheDocument();
    expect(within(rows[0]).getByText('즉시 확인')).toBeInTheDocument();
  });

  it('고위험 batbayar 행 액션은 "승인"이 아니라 "검토"다 (C10)', () => {
    renderAt('/');
    const queue = screen.getByLabelText('우선 처리 케이스');
    const batbayarRow = within(queue).getByText('Batbayar E.').closest('li') as HTMLElement;
    expect(within(batbayarRow).getByRole('button', { name: '검토' })).toBeInTheDocument();
    expect(within(batbayarRow).queryByRole('button', { name: '승인' })).not.toBeInTheDocument();
  });

  it('행 액션 클릭이 케이스로 이동한다', async () => {
    const router = renderAt('/');
    const queue = screen.getByLabelText('우선 처리 케이스');
    const nguyenRow = within(queue).getByText('Nguyen Van A').closest('li') as HTMLElement;
    fireEvent.click(within(nguyenRow).getByRole('button', { name: '승인' }));
    // /case/:caseId loader가 비동기라 내비게이션 커밋을 기다린다.
    await waitFor(() => expect(router.state.location.pathname).toBe('/case/nguyen'));
  });

  it('우측 레일에 실시간 활동·감사 로그·전체 보기 링크가 있다', () => {
    renderAt('/');
    const rail = screen.getByRole('complementary', { name: '활동·감사 레일' });
    expect(within(rail).getByText('실시간 에이전트 활동')).toBeInTheDocument();
    expect(within(rail).getByRole('button', { name: '전체 보기' })).toBeInTheDocument();
  });
});

describe('ControlTowerPage 모바일 게이트', () => {
  it('모바일 "/"는 컨트롤 타워가 아니라 오늘 브리핑을 렌더한다', () => {
    mockViewport(false);
    renderAt('/');
    expect(screen.queryByRole('region', { name: '컨트롤 타워' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '오늘 브리핑' })).toBeInTheDocument();
  });
});
