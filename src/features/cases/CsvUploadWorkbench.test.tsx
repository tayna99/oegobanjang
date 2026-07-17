import { act } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

// jsdom엔 matchMedia가 없다 — CaseWorkbench.test.tsx와 동일한 관례로 데스크톱을 흉내낸다.
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
  useEvidenceStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  useRoleStore.getState().reset();
  vi.useRealTimers();
});

// 4.4 DoD ② — "성공 시 근로자 N명 스토어 반영 테스트".
describe('CsvUploadWorkbench (PC, 4.4 DoD)', () => {
  beforeEach(() => {
    mockViewport(true);
    vi.useFakeTimers();
  });

  it('샘플 불러오기 → 검증 → 정상 6명만 등록하면 caseStore에 6건이 반영된다', () => {
    renderAt('/cases/import');

    expect(screen.getByRole('heading', { name: '근로자 정보 일괄 등록' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '샘플 CSV 불러오기' }));

    act(() => {
      vi.advanceTimersByTime(1200);
    });

    expect(screen.getByText('전체 8')).toBeInTheDocument();
    expect(screen.getByText('정상 6')).toBeInTheDocument();
    expect(screen.getByText('경고 1')).toBeInTheDocument();
    expect(screen.getByText('오류 1')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '정상 6명만 등록' }));

    const cases = useCaseStore.getState().cases;
    const importedCases = Object.values(cases).filter((c) => c.caseId.startsWith('imp-'));
    expect(importedCases).toHaveLength(6);
    expect(cases['imp-kyaw-zin']).toBeUndefined();
    expect(cases['imp-pham-duc-m']).toBeUndefined();

    expect(useEvidenceStore.getState().events.some((e) => e.summary === 'CSV 일괄 등록 — 근로자 6명 반영')).toBe(true);
    expect(screen.getByText('정상 6명이 등록되었습니다')).toBeInTheDocument();
  });

  it('오류 필터를 누르면 오류 행 1건만 보인다', () => {
    renderAt('/cases/import');
    fireEvent.click(screen.getByRole('button', { name: '샘플 CSV 불러오기' }));
    act(() => {
      vi.advanceTimersByTime(1200);
    });

    fireEvent.click(screen.getByRole('button', { name: '오류 1' }));
    expect(screen.getByText('Kyaw Zin')).toBeInTheDocument();
    expect(screen.queryByText('Nguyen Van A')).not.toBeInTheDocument();
  });

  // NEXT_ROADMAP B-4 회귀: "템플릿 다운로드"는 onClick이 없던 죽은 버튼이었다.
  it('템플릿 다운로드 버튼을 누르면 CSV 다운로드가 실행된다', () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    renderAt('/cases/import');

    fireEvent.click(screen.getByRole('button', { name: '템플릿 다운로드' }));

    expect(clickSpy).toHaveBeenCalledOnce();
    clickSpy.mockRestore();
  });

  it('열람자·대표 권한으로는 등록 화면 대신 안내 문구만 보인다', () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/cases/import');
    expect(screen.getByText('CSV 일괄 등록은 담당자 권한으로만 이용할 수 있습니다.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '샘플 CSV 불러오기' })).not.toBeInTheDocument();
  });
});
