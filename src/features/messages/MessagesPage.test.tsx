import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useThreadStore } from '@/stores/threadStore';

function renderAt(path: string) {
  useThreadStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

describe('MessagesPage', () => {
  beforeEach(() => {
    useThreadStore.getState().reset();
  });

  it('threadStore가 비어 있으면 THREADS로 시드해 정렬된 행 3개를 렌더한다', () => {
    renderAt('/messages');

    expect(screen.getByRole('heading', { name: '메시지' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tran T.H.' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nguyen V.' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bayar M.' })).toBeInTheDocument();
  });

  it('배지 라벨과 하단 고정 캡션을 보여준다', () => {
    renderAt('/messages');

    expect(screen.getByText('응답 도착')).toBeInTheDocument();
    expect(screen.getByText('승인 대기')).toBeInTheDocument();
    expect(screen.getByText('발송됨')).toBeInTheDocument();
    expect(screen.getByText('모든 메시지는 승인 후에만 발송됩니다')).toBeInTheDocument();
  });

  it('nguyen 행은 승인 대기 초안이라 탭하면 케이스 초안(M3)로 직행한다', async () => {
    const router = renderAt('/messages');

    fireEvent.click(screen.getByRole('button', { name: 'Nguyen V.' }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/case/nguyen/draft'));
  });

  it('tran 행을 탭하면 스레드 상세 경로로 이동한다', async () => {
    const router = renderAt('/messages');

    fireEvent.click(screen.getByRole('button', { name: 'Tran T.H.' }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/thread/tran'));
  });

  it('렌더된 DOM에 근로자 원문 문장(베트남어·몽골어)이 노출되지 않는다(PII 가드)', () => {
    renderAt('/messages');

    expect(document.body.textContent).not.toMatch(/Chào anh Tran/);
    expect(document.body.textContent).not.toMatch(/Hợp đồng lao động/);
    expect(document.body.textContent).not.toMatch(/Сайн байна уу/);
  });
});
