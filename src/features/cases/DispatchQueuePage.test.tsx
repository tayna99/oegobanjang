import { fireEvent, render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { DISPATCH_QUEUE } from '@/mocks/dispatch';
import { useEvidenceStore } from '@/stores/evidenceStore';
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
  useEvidenceStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  useRoleStore.getState().reset();
});

describe('DispatchQueuePage (PC 4d)', () => {
  beforeEach(() => mockViewport(true));

  it('실행 대기 큐와 오늘 실행 이력을 보여준다', () => {
    renderAt('/cases/dispatch');
    expect(screen.getByRole('heading', { name: '발송 실행' })).toBeInTheDocument();
    expect(screen.getByText(`실행 대기 ${DISPATCH_QUEUE.length}건 · 오늘 실행 2건`)).toBeInTheDocument();
    expect(screen.getByText('서류요청 메시지 발송 (VN)')).toBeInTheDocument();
    expect(screen.getByText('실행 완료 · 응답 수신')).toBeInTheDocument();
  });

  it('발송 실행(mock)을 누르면 evidence(dispatch_executed)가 남고 큐에서 사라진다', () => {
    renderAt('/cases/dispatch');
    const executeButtons = screen.getAllByRole('button', { name: '발송 실행 (mock)' });
    fireEvent.click(executeButtons[0]);

    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'dispatch_executed' && e.caseId === 'nguyen'),
    ).toBe(true);
    expect(screen.getByText(`실행 대기 ${DISPATCH_QUEUE.length - 1}건 · 오늘 실행 2건`)).toBeInTheDocument();
  });

  it('행정사 패키지 전달 항목은 "링크 발급" 버튼을 보여준다', () => {
    renderAt('/cases/dispatch');
    expect(screen.getByRole('button', { name: '링크 발급' })).toBeInTheDocument();
  });

  it('열람자·대표 권한으로는 안내 문구만 보인다', () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/cases/dispatch');
    expect(screen.getByText('발송 실행 큐는 담당자 권한으로만 이용할 수 있습니다.')).toBeInTheDocument();
  });

  it('비데스크톱에서는 PC 유도 안내만 보인다', () => {
    mockViewport(false);
    renderAt('/cases/dispatch');
    expect(screen.getByText('발송 실행 큐는 PC에서 이용해 주세요')).toBeInTheDocument();
  });
});
