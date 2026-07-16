import { fireEvent, render, screen, within } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

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
});

// PC 메시지(4c, 부분 구현) — M6 해석확인이 PC 워크벤치에서도 evidence+합법 전이 규칙을 지킨다.
describe('MessagesWorkbench (PC)', () => {
  beforeEach(() => mockViewport(true));

  it('/messages로 직접 진입해도 3열(스레드 목록·대화·연결 케이스)이 렌더되고 연결 케이스가 보인다', () => {
    renderAt('/messages');
    expect(screen.getByRole('navigation', { name: '스레드 목록' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Tran Thi H.' })).toBeInTheDocument();
    const linkedCase = screen.getByRole('complementary', { name: '연결 케이스' });
    expect(within(linkedCase).getByText('계약-체류 만료일 불일치 검토')).toBeInTheDocument();
  });

  it('해석 확인 시 evidence가 기록되고 합법 전이(risk_review→approval_pending)면 케이스 상태가 반영된다', () => {
    renderAt('/messages');
    expect(useCaseStore.getState().cases.tranCase.state).toBe('risk_review');
    fireEvent.click(screen.getByRole('button', { name: '해석 확인 · 상태 반영' }));
    expect(useCaseStore.getState().cases.tranCase.state).toBe('approval_pending');
    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'final_response_generated' && e.caseId === 'tranCase'),
    ).toBe(true);
    // 확인 후엔 대화 패널·연결 케이스 레일 모두 "케이스 열기" 버튼을 보여준다(중복 허용).
    expect(screen.getAllByRole('button', { name: '케이스 열기' }).length).toBeGreaterThanOrEqual(2);
  });

  it('스레드 선택이 대화·연결 케이스를 함께 바꾼다', () => {
    renderAt('/messages');
    fireEvent.click(screen.getByRole('button', { name: /Nguyen Van A/ }));
    expect(screen.getByRole('heading', { name: 'Nguyen Van A' })).toBeInTheDocument();
    const linkedCase = screen.getByRole('complementary', { name: '연결 케이스' });
    expect(within(linkedCase).getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
  });
});

describe('MessagesPage 모바일 게이트', () => {
  it('비데스크톱에서는 기존 모바일 스레드 목록이 렌더된다', () => {
    mockViewport(false);
    renderAt('/messages');
    expect(screen.queryByRole('navigation', { name: '스레드 목록' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '메시지' })).toBeInTheDocument();
  });
});
