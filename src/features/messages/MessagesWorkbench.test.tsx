import { fireEvent, render, screen, within } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useThreadStore } from '@/stores/threadStore';

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
  useThreadStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
});

// PC 메시지(4c, D-1 재배선 완료) — mocks/threads.ts/threadStore를 모바일과 공유하는 단일
// 데이터 소스로 쓴다(이전엔 독립 mock(mocks/messages.ts)이었다 — NEXT_ROADMAP D-1, 2026-07-17).
// M6 해석확인은 ThreadPage(모바일)와 동일한 오케스트레이션(confirmInterpretation→
// applyInterpretationUpdates→evidence append)을 그대로 따른다 — case state 전이는 하지 않는다.
describe('MessagesWorkbench (PC)', () => {
  beforeEach(() => mockViewport(true));

  it('/messages로 직접 진입해도 3열(스레드 목록·대화·연결 케이스)이 렌더되고 응답 도착 스레드(Tran)가 기본 선택된다', () => {
    renderAt('/messages');
    expect(screen.getByRole('navigation', { name: '스레드 목록' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Tran T.H.' })).toBeInTheDocument();
    const linkedCase = screen.getByRole('complementary', { name: '연결 케이스' });
    expect(within(linkedCase).getByText('계약-체류 만료일 불일치 검토')).toBeInTheDocument();
  });

  it('해석 확인 시 threadStore·evidenceStore·caseStore.docUpdates가 모바일(ThreadPage)과 동일하게 갱신된다', () => {
    renderAt('/messages');
    expect(useCaseStore.getState().cases.tranCase.state).toBe('risk_review');

    fireEvent.click(screen.getByRole('button', { name: '해석 확인 · 상태 반영' }));

    // 해석 확인은 케이스 상태를 전이시키지 않는다(caseStore.applyInterpretationUpdates 계약 —
    // ThreadPage.test.tsx와 동일 기준). 이전 PC 전용 mock 시절엔 여기서 임의로
    // risk_review→approval_pending 전이를 했었는데, 그건 모바일과 어긋나는 독자 로직이었다.
    expect(useCaseStore.getState().cases.tranCase.state).toBe('risk_review');
    const confirmed = useEvidenceStore
      .getState()
      .events.filter((e) => e.type === 'interpretation_confirmed');
    expect(confirmed).toHaveLength(1);
    expect(confirmed[0].caseId).toBe('tranCase');
    expect(confirmed[0].evidenceRef).toBe('#4791');
    expect(useCaseStore.getState().docUpdates.tranCase?.['표준근로계약서']).toEqual({ to: '회사 확인 필요' });
    // 확인 후엔 대화 패널·연결 케이스 레일 모두 "케이스 열기" 버튼을 보여준다(중복 허용) —
    // 확인 직후에도 지금 열려 있던 스레드(Tran)가 그대로 보여야 한다(정렬 재계산으로 다른
    // 스레드로 튀지 않는다).
    expect(screen.getByRole('heading', { name: 'Tran T.H.' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '케이스 열기' }).length).toBeGreaterThanOrEqual(2);
  });

  it('스레드 선택이 대화·연결 케이스를 함께 바꾼다 — 승인 대기 초안(draftCaseId)도 연결 케이스가 보인다', () => {
    renderAt('/messages');
    fireEvent.click(screen.getByRole('button', { name: /Nguyen V\./ }));
    expect(screen.getByRole('heading', { name: 'Nguyen V.' })).toBeInTheDocument();
    expect(screen.getByText('아직 발송되지 않았습니다 — 승인 후 발송됩니다.')).toBeInTheDocument();
    const linkedCase = screen.getByRole('complementary', { name: '연결 케이스' });
    expect(within(linkedCase).getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
  });

  it('근로자 원문 문장(베트남어)이 스레드 목록 미리보기에는 노출되지 않는다(GOTCHAS §3 — 스레드 내부는 허용)', () => {
    renderAt('/messages');
    const list = screen.getByRole('navigation', { name: '스레드 목록' });
    expect(list.textContent).not.toMatch(/Hợp đồng lao động/);
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
