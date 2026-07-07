import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';

function renderAt(path: string) {
  useCaseStore.getState().reset();
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
    expect(screen.getByRole('button', { name: /Bayar M\./ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Nguyen V\./ })).not.toBeInTheDocument();
  });

  it('clears an applied preset back to the full case list', () => {
    renderAt('/cases?filter=approval');

    expect(screen.getByText('적용됨: 승인 대기')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '해제' }));

    expect(screen.queryByText('적용됨: 승인 대기')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nguyen V\./ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Bayar M\./ })).toBeInTheDocument();
  });

  it('opens the case sheet from a compact list item', async () => {
    const router = renderAt('/cases');

    fireEvent.click(screen.getByRole('button', { name: /Tran T\.H\./ }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/case/tranCase'));
  });
});