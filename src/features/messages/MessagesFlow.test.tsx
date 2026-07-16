import { fireEvent, render, screen, within } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

afterEach(() => {
  useEvidenceStore.getState().reset();
  useCaseStore.getState().reset();
});

function renderAt(path: string) {
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

// 2.2 메시지 탭 + 스레드 + M6 응답 해석.
describe('MessagesPage — 목록', () => {
  it('스레드 목록을 상태 라벨로 보여주고 근로자 원문은 노출하지 않는다', () => {
    renderAt('/messages');
    expect(screen.getByRole('heading', { name: '메시지' })).toBeInTheDocument();
    expect(screen.getByText('Tran Thi H.')).toBeInTheDocument();
    expect(screen.getByText('응답 도착 · 해석 필요')).toBeInTheDocument();
    // 근로자 베트남어 원문은 목록에 없다(스레드 내부에서만) — GOTCHAS §3.
    expect(screen.queryByText(/Hợp đồng công ty/)).not.toBeInTheDocument();
  });

  it('스레드 탭 시 대화 뷰로 이동한다', async () => {
    const router = renderAt('/messages');
    fireEvent.click(screen.getByRole('button', { name: 'Tran Thi H. 대화' }));
    await screen.findByRole('heading', { name: 'Tran Thi H.' });
    expect(router.state.location.pathname).toBe('/thread/tranCase');
  });
});

describe('ThreadPage — M6 응답 해석', () => {
  it('스레드 내부에서는 근로자 원문과 KR 요약을 함께 보여준다', async () => {
    renderAt('/thread/tranCase');
    await screen.findByRole('heading', { name: 'Tran Thi H.' });
    // 원문은 스레드 내부에서만 노출.
    expect(screen.getByText(/Hợp đồng công ty giữ/)).toBeInTheDocument();
    expect(screen.getByText(/계약서는 회사가 보관 중이며/)).toBeInTheDocument();
    expect(screen.getByText('담당자 확인 필요')).toBeInTheDocument();
  });

  it('해석 확인 시 evidence가 기록되고 확인 상태로 바뀐다(DoD)', async () => {
    renderAt('/thread/tranCase');
    await screen.findByRole('heading', { name: 'Tran Thi H.' });
    fireEvent.click(screen.getByRole('button', { name: '해석 확인 · 상태 반영' }));

    const section = screen.getByRole('region', { name: '응답 해석' });
    expect(within(section).getByText('확인됨')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '케이스 열기' })).toBeInTheDocument();

    const events = useEvidenceStore.getState().events.filter((e) => e.type === 'interpretation_confirmed');
    expect(events.some((e) => e.caseId === 'tranCase' && e.summary?.includes('응답 해석 확인'))).toBe(true);
  });

  it('해석 확인 시 제안된 문서 상태 갱신이 caseStore.docUpdates에 반영된다(main 이식)', async () => {
    renderAt('/thread/tranCase');
    await screen.findByRole('heading', { name: 'Tran Thi H.' });
    fireEvent.click(screen.getByRole('button', { name: '해석 확인 · 상태 반영' }));

    const docUpdates = useCaseStore.getState().docUpdates['tranCase'];
    expect(docUpdates?.['표준근로계약서']).toEqual({ to: '회사 확인 필요' });
    expect(docUpdates?.['여권 사본']).toEqual({ to: '제출 예정 · 내일' });
  });

  it('해석 확인 시 케이스 상태도 승인 대기로 전환된다(버튼 라벨 "상태 반영"과 실제 동작 일치, 코드리뷰 지적 교정)', async () => {
    renderAt('/thread/tranCase');
    await screen.findByRole('heading', { name: 'Tran Thi H.' });
    expect(useCaseStore.getState().cases['tranCase']?.state).toBe('risk_review');
    fireEvent.click(screen.getByRole('button', { name: '해석 확인 · 상태 반영' }));
    expect(useCaseStore.getState().cases['tranCase']?.state).toBe('approval_pending');
  });

  it('응답이 없는 스레드(nguyen)는 해석 카드가 없다', async () => {
    renderAt('/thread/nguyen');
    await screen.findByRole('heading', { name: 'Nguyen Van A' });
    expect(screen.queryByRole('region', { name: '응답 해석' })).not.toBeInTheDocument();
  });
});
