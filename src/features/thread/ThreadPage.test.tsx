import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { threadBadge } from '@/lib/threads';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useThreadStore } from '@/stores/threadStore';

function renderAt(path: string) {
  useThreadStore.getState().reset();
  useCaseStore.getState().reset();
  useEvidenceStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

describe('ThreadPage', () => {
  beforeEach(() => {
    useThreadStore.getState().reset();
    useCaseStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  it('스레드가 없으면 인라인 안내와 메시지 탭으로 링크를 보여준다', async () => {
    renderAt('/thread/does-not-exist');

    // /thread/:threadId는 loader가 있는 라우트라 초기 데이터 로드 틱을 기다려야 한다.
    expect(await screen.findByText('스레드를 찾을 수 없습니다.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '메시지 탭으로' })).toBeInTheDocument();
  });

  it('승인 대기 초안(draftCaseId, 미발송) 스레드는 M3 초안으로 즉시 리다이렉트된다', async () => {
    const router = renderAt('/thread/nguyen');
    await waitFor(() => expect(router.state.location.pathname).toBe('/case/nguyen/draft'));
  });

  it('응답 도착 스레드는 M6 해석 모드로 진입하고 원문은 접힌 상태다', async () => {
    renderAt('/thread/tran');

    expect(await screen.findByText('응답 도착 · Tran T.H.')).toBeInTheDocument();
    expect(screen.getByText('담당자 확인 필요')).toBeInTheDocument();
    expect(screen.queryByText(/công ty đang giữ/)).not.toBeInTheDocument();
  });

  describe('DoD — 해석 확인 시 상태 갱신 + evidence', () => {
    it('[상태 반영 확인] 클릭 시 스토어 3종이 모두 갱신되고 화면이 타임라인으로 전환된다', async () => {
      const router = renderAt('/thread/tran');

      // 진입 시점: M6 해석 모드, InterpretationCard 렌더.
      expect(await screen.findByText('담당자 확인 필요')).toBeInTheDocument();

      const confirmButton = screen.getByRole('button', { name: '상태 반영 확인' });
      fireEvent.click(confirmButton);
      // 이중 클릭 방지: 같은(이미 화면에서 사라졌을 수 있는) 버튼을 다시 눌러도 안전해야 한다.
      fireEvent.click(confirmButton);

      // (a) threadStore: tran 스레드 interpretationStatus가 confirmed.
      expect(useThreadStore.getState().threads.tran.interpretationStatus).toBe('confirmed');

      // (b) evidenceStore: interpretation_confirmed 1건, caseId/evidenceRef 일치, 원문 미포함.
      const confirmedEvents = useEvidenceStore
        .getState()
        .events.filter((e) => e.type === 'interpretation_confirmed');
      expect(confirmedEvents).toHaveLength(1);
      expect(confirmedEvents[0].caseId).toBe('tranCase');
      expect(confirmedEvents[0].evidenceRef).toBe('#4791');
      expect(confirmedEvents[0].summary).not.toMatch(/Hợp đồng lao động/);
      expect(confirmedEvents[0].summary).not.toMatch(/công ty đang giữ/);

      // (c) caseStore.docUpdates: 표준근로계약서·여권 사본 두 필드 갱신.
      const docUpdates = useCaseStore.getState().docUpdates.tranCase;
      expect(docUpdates?.['표준근로계약서']).toEqual({ to: '회사 확인 필요' });
      expect(docUpdates?.['여권 사본']).toEqual({ to: '제출 예정 · 내일' });

      // (d) 화면은 timeline 모드로 전환 — 확인 버튼 사라짐, confirmedCardText 렌더.
      expect(screen.queryByRole('button', { name: '상태 반영 확인' })).not.toBeInTheDocument();
      expect(
        screen.getByText('상태 반영 완료 — 계약서 회사 확인 · 여권 제출 대기 (판단 기록 #4791)'),
      ).toBeInTheDocument();

      // (e) /messages로 이동하면 tran 행 배지가 확인 완료로 바뀐다(threadBadge 검증).
      await act(async () => {
        await router.navigate('/messages');
      });
      expect(screen.getByText('확인 완료')).toBeInTheDocument();
      expect(threadBadge(useThreadStore.getState().threads.tran)).toEqual({
        label: '확인 완료',
        tone: 'neutral',
      });
    });
  });
});
