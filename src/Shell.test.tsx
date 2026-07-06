import { act, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { Shell } from './Shell';

function renderShell(initialPath: string) {
  const router = createMemoryRouter(
    [
      {
        element: <Shell />,
        children: [
          { index: true, element: <p>M1 자리</p> },
          { path: 'cases', element: <p>M7 자리</p> },
          { path: 'case/:caseId/approve', element: <p>M4 자리</p> },
        ],
      },
    ],
    { initialEntries: [initialPath] },
  );
  const utils = render(<RouterProvider router={router} />);
  return { router, ...utils };
}

describe('Shell', () => {
  it('모바일 탭바 4개를 렌더한다', () => {
    renderShell('/');
    // vitest.config.ts의 test.css: false로 인해 이 테스트 환경에서는 Tailwind의
    // hidden/lg: 클래스가 실제 스타일로 반영되지 않아 PC 헤더 nav와 모바일 탭바
    // nav가 동시에 접근성 트리에 노출된다(실제 브라우저에서는 CSS로 하나만
    // 보이므로 문제 없음). 라벨 중복 매치를 피하기 위해 모바일 탭바
    // (aria-label="모바일 탭바")로 쿼리를 좁힌다 — 검증 내용(4개 탭 링크 존재)은
    // 그대로다.
    const tabBar = screen.getByRole('navigation', { name: '모바일 탭바' });
    expect(within(tabBar).getByRole('link', { name: /브리핑/ })).toBeInTheDocument();
    expect(within(tabBar).getByRole('link', { name: /케이스/ })).toBeInTheDocument();
    expect(within(tabBar).getByRole('link', { name: /메시지/ })).toBeInTheDocument();
    expect(within(tabBar).getByRole('link', { name: /기록/ })).toBeInTheDocument();
  });

  it('현재 위치의 자식 라우트를 Outlet에 렌더한다', () => {
    renderShell('/cases');
    expect(screen.getByText('M7 자리')).toBeInTheDocument();
  });

  it('루트("/")로 바로 진입하면 히스토리를 건드리지 않는다', async () => {
    const { router } = renderShell('/');
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(router.state.location.key).toBe('default');
  });

  // vitest 3.x + Node 24 + jsdom 조합에서 router.navigate(-1)(POP 내비게이션)이
  // AbortSignal 브랜드 체크 문제로 예외를 던지던 환경 버그가 있었다(vitest#8374).
  // vitest 4.x로 업그레이드하며 수정되어 정상 통과한다.
  it('딥링크로 바로 진입하면 뒤로가기가 M1(홈)으로 떨어진다', async () => {
    const { router } = renderShell('/case/nguyen/approve');
    await screen.findByText('M4 자리');
    await waitFor(() =>
      expect(router.state.location.pathname).toBe('/case/nguyen/approve'),
    );

    await act(async () => {
      await router.navigate(-1);
    });
    expect(router.state.location.pathname).toBe('/');
  });
});
