import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import type { CaseCard } from '@/types';

function renderAt(path: string, seedCards?: CaseCard[]) {
  useCaseStore.getState().reset();
  seedCards?.forEach(useCaseStore.getState().upsert);
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

describe('CaseListPage', () => {
  it('renders a deep-linked immediate filter with deterministic grouped results', () => {
    renderAt('/cases?filter=crit');

    expect(screen.getByRole('heading', { name: '케이스' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '즉시 확인' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('적용됨: 즉시 확인')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '즉시 확인 · 1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /체류기간 만료 경과/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /체류기간 연장 서류 요청/ })).not.toBeInTheDocument();
  });

  it('clears an applied preset back to the full case list', () => {
    renderAt('/cases?filter=approval');

    expect(screen.getByText('적용됨: 승인 대기')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '해제' }));

    expect(screen.queryByText('적용됨: 승인 대기')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /체류기간 연장 서류 요청/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /체류기간 만료 경과/ })).toBeInTheDocument();
  });

  it('opens the case sheet from a compact list item', async () => {
    const router = renderAt('/cases');

    fireEvent.click(screen.getByRole('button', { name: /계약-체류 만료일 불일치 검토/ }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/case/tranCase'));
  });

  it('keeps completed cases reachable behind a collapsed group header', () => {
    const completed = {
      ...CASE_CARDS[0],
      caseId: 'done-nguyen',
      title: 'Nguyen V. 승인 완료',
      state: 'human_approved',
    } satisfies CaseCard;

    renderAt('/cases', [completed]);

    expect(screen.getByRole('button', { name: /완료 · 1/ })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('button', { name: /Nguyen V\. 승인 완료/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /완료 · 1/ }));

    expect(screen.getByRole('button', { name: /완료 · 1/ })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('button', { name: /Nguyen V\. 승인 완료/ })).toBeInTheDocument();
  });

  it('returns to the filtered case list after opening and closing a case sheet', async () => {
    const router = renderAt('/cases?filter=info');

    fireEvent.click(screen.getByRole('button', { name: /계약-체류 만료일 불일치 검토/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/case/tranCase'));
    // /case/:caseId loader가 비동기라 router state 갱신 후에도 DOM 커밋이 한 틱 늦을 수
    // 있다(전체 스위트에서만 간헐 실패하던 원인). 시트 DOM이 실제로 나타날 때까지 기다린다.
    const scrim = await screen.findByTestId('bottom-sheet-scrim', {}, { timeout: 5000 });
    expect(screen.getByText('적용됨: 확인 필요')).toBeInTheDocument();

    fireEvent.click(scrim);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/cases');
      expect(router.state.location.search).toBe('?filter=info');
    });
  });
});