import { fireEvent, render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useRoleStore } from '@/stores/roleStore';

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
  useRoleStore.getState().reset();
});

describe('WorkerDataWorkbench (PC 4b)', () => {
  beforeEach(() => mockViewport(true));

  it('워크벤치를 통해 도달하면 시드된 6인 로스터를 근로자 목록으로 보여준다', () => {
    renderAt('/cases');
    fireEvent.click(screen.getByRole('button', { name: '근로자 데이터' }));
    expect(screen.getByRole('heading', { name: '근로자' })).toBeInTheDocument();
    expect(screen.getByText('Nguyen Van A')).toBeInTheDocument();
    expect(screen.getByText('E-9 · 6명 · 상태는 DB가 진실의 원천(RAG에 저장하지 않음)')).toBeInTheDocument();
  });

  it('CSV 가져오기 버튼이 /cases/import로 이동한다', () => {
    const router = renderAt('/cases/workers');
    fireEvent.click(screen.getByRole('button', { name: 'CSV로 일괄 등록' }));
    expect(router.state.location.pathname).toBe('/cases/import');
  });

  // 회귀: CaseWorkbench를 거치지 않고 /cases/workers로 바로 진입해도(딥링크) 스토어가
  // 비어 있으면 자체적으로 로스터를 시드해야 한다 — 브라우저 실검증에서 발견된 버그.
  it('/cases/workers로 직접 진입해도 caseStore가 비어 있으면 로스터를 시드한다', () => {
    const router = renderAt('/cases/workers');
    expect(router.state.location.pathname).toBe('/cases/workers');
    expect(screen.getByText('E-9 · 6명 · 상태는 DB가 진실의 원천(RAG에 저장하지 않음)')).toBeInTheDocument();
    expect(screen.getByText('Nguyen Van A')).toBeInTheDocument();
  });

  it('열람자·대표 권한으로는 안내 문구만 보인다', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/cases/workers');
    expect(screen.getByText('근로자 데이터 관리는 담당자 권한으로만 이용할 수 있습니다.')).toBeInTheDocument();
  });

  it('비데스크톱에서는 PC 유도 안내만 보인다', () => {
    mockViewport(false);
    renderAt('/cases/workers');
    expect(screen.getByText('근로자 데이터 관리는 PC에서 이용해 주세요')).toBeInTheDocument();
  });
});
