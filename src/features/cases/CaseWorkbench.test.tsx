import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';

// jsdom에는 matchMedia가 없다 — useIsDesktop 분기 덕에 기존 모바일 테스트는
// 워크벤치를 전혀 만나지 않는다. 여기서는 데스크톱을 명시적으로 흉내낸다.
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
  // 다른 테스트 파일 환경을 오염시키지 않도록 원복.
  delete (window as { matchMedia?: unknown }).matchMedia;
});

describe('CaseWorkbench (PC, M2.5.4 DoD)', () => {
  beforeEach(() => {
    mockViewport(true);
  });

  it('3열(목록 레일·상세·AI 레일)을 렌더하고 첫 케이스를 기본 선택한다', () => {
    renderAt('/cases');

    expect(screen.getByRole('region', { name: '케이스 워크벤치' })).toBeInTheDocument();
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });
    const detail = screen.getByRole('region', { name: '케이스 상세' });
    const evidenceRail = screen.getByRole('complementary', { name: 'AI·근거 레일' });
    expect(listRail).toBeInTheDocument();
    expect(evidenceRail).toBeInTheDocument();

    // 자동 선택: 그룹·정렬 규칙(lib/cases)상 첫 케이스 = siti(승인 대기·HIGH·D-3).
    expect(
      within(detail).getByRole('heading', { name: '고용변동 신고 기한 임박' }),
    ).toBeInTheDocument();
    // CTA는 데이터 구동 라벨 그대로(카피 창작 금지) + 근거 있음 → 잠금 아님.
    expect(within(detail).getByRole('button', { name: '승인하기' })).toBeEnabled();
    // 진행 스테퍼의 현재 단계.
    expect(within(screen.getByRole('list', { name: '진행 단계' })).getByText('승인 대기')).toBeInTheDocument();
    // 고정 가드레일 문구 2종.
    expect(within(detail).getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();
    expect(within(evidenceRail).getByText('가능/불가능 판단은 제공하지 않습니다.')).toBeInTheDocument();
  });

  it('목록 행 클릭이 URL(/case/:caseId)과 상세 패널을 동기화한다', async () => {
    const router = renderAt('/cases');
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });

    fireEvent.click(within(listRail).getByRole('button', { name: /체류기간 만료 경과/ }));

    // /case/:caseId loader가 비동기라 router state보다 DOM 커밋이 늦을 수 있다 — DOM 기준으로 대기.
    // 전체 스위트 병렬 부하에서 기본 1초가 모자랄 수 있어 여유를 준다.
    await screen.findByRole('heading', { name: '체류기간 만료 경과 · 행정사 검토' });
    expect(router.state.location.pathname).toBe('/case/batbayar');
    const detail = screen.getByRole('region', { name: '케이스 상세' });
    // bayar 가드노트가 상세에 노출된다.
    expect(within(detail).getByText(/행정사 검토로만 진행됩니다/)).toBeInTheDocument();
  });

  it('필터 컨텍스트가 행 클릭 후에도 목록 레일에 유지된다', async () => {
    const router = renderAt('/cases?filter=approval');
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });

    fireEvent.click(within(listRail).getByRole('button', { name: /체류기간 연장 서류 요청/ }));
    await screen.findByRole('heading', { name: '체류기간 연장 서류 요청' });
    await waitFor(() => expect(router.state.location.pathname).toBe('/case/nguyen'));

    const railAfter = screen.getByRole('navigation', { name: '케이스 목록 레일' });
    expect(within(railAfter).getByRole('button', { name: /^승인 대기 \d/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    // 승인 대기 프리셋: siti·nguyen만 남는다(6인 로스터).
    expect(within(railAfter).queryByRole('button', { name: /계약-체류 만료일 불일치/ })).not.toBeInTheDocument();
  });

  it('딥링크 /case/:caseId가 해당 케이스를 선택 상태로 연다', async () => {
    renderAt('/case/tranCase');
    // /case/:caseId 라우트는 loader(validateIdParam)가 있어 첫 렌더가 비동기다.
    const detail = await screen.findByRole('region', { name: '케이스 상세' });
    expect(
      within(detail).getByRole('heading', { name: '계약-체류 만료일 불일치 검토' }),
    ).toBeInTheDocument();
  });

  it('검색어가 목록 레일을 제목·근로자명 기준으로 거른다', () => {
    renderAt('/cases');
    fireEvent.change(screen.getByRole('searchbox', { name: '케이스 검색' }), {
      target: { value: '존재하지않는검색어' },
    });
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });
    expect(within(listRail).getByText('조건에 맞는 케이스가 없습니다')).toBeInTheDocument();

    // 근로자명 매칭("이름, 케이스 검색" — §3b placeholder): 제목엔 없는 이름으로도 찾는다.
    fireEvent.change(screen.getByRole('searchbox', { name: '케이스 검색' }), {
      target: { value: 'Nguyen' },
    });
    expect(within(listRail).getByRole('button', { name: /체류기간 연장 서류 요청/ })).toBeInTheDocument();
  });
});

describe('CaseWorkbench 모바일 게이트 (모바일 회귀 없음)', () => {
  it('비데스크톱에서는 워크벤치가 마운트되지 않고 기존 모바일 목록이 렌더된다', () => {
    mockViewport(false);
    renderAt('/cases');

    expect(screen.queryByRole('region', { name: '케이스 워크벤치' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '케이스' })).toBeInTheDocument();
  });
});
