import { render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { App } from '@/App';

describe('App', () => {
  it('renders the empty shell', () => {
    const router = createMemoryRouter(
      [{ path: '/', element: <App /> }],
      { initialEntries: ['/'] },
    );
    render(<RouterProvider router={router} />);
    expect(
      screen.getByRole('heading', { name: '외고반장' }),
    ).toBeInTheDocument();
  });
});
