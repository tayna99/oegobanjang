import { act, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { routeConfig } from './router';

function summarize(routes: RouteObject[]): unknown {
  return routes.map((r) => ({
    path: r.path ?? (r.index ? '(index)' : '(layout)'),
    hasLoader: Boolean(r.loader),
    children: r.children ? summarize(r.children) : undefined,
  }));
}

describe('routeConfig', () => {
  it('딥링크 맵과 1:1 대응하는 경로 구조를 유지한다', () => {
    expect(summarize(routeConfig)).toMatchSnapshot();
  });
});

describe('딥링크 진입', () => {
  it('/case/:id/approve로 바로 진입하면 M4가 렌더되고 뒤로가기는 M1로 떨어진다', async () => {
    const router = createMemoryRouter(routeConfig, {
      initialEntries: ['/case/nguyen/approve'],
    });
    render(<RouterProvider router={router} />);

    await screen.findByText('승인 전 확인');
    await waitFor(() =>
      expect(router.state.location.pathname).toBe('/case/nguyen/approve'),
    );

    await act(async () => {
      await router.navigate(-1);
    });
    expect(router.state.location.pathname).toBe('/');
  });

  it('허용되지 않은 caseId 형식이면 M1로 리다이렉트된다', async () => {
    const router = createMemoryRouter(routeConfig, {
      initialEntries: ['/case/a%20b/approve'],
    });
    render(<RouterProvider router={router} />);
    await screen.findByText(/그린푸드 제조/);
  });
});
