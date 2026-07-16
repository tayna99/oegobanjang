import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { Interpretation, MessageThread } from '@/types';
import { ThreadScreen } from './ThreadScreen';
import type { ThreadViewState } from './ThreadScreen';

const INTERPRETATION: Interpretation = {
  interpretationId: 'tran-interp-1',
  threadId: 'tran',
  caseId: 'tranCase',
  summaryKo: '표준근로계약서는 회사가 보관 중이라고 답했습니다.',
  confidence: 'high',
  updates: [{ updateId: 'tran-doc-contract', field: '표준근로계약서', from: '누락', to: '회사 확인 필요', badgeTone: 'warning' }],
  recommendedActions: [],
  isFinal: false,
  confirmedSummary: 'Tran 응답 해석 확인 — 서류 상태 2건 갱신',
  confirmedCardText: '상태 반영 완료 — 계약서 회사 확인 · 여권 제출 대기 (판단 기록 #4791)',
  evidenceRef: '#4791',
};

const TRAN_THREAD: MessageThread = {
  threadId: 'tran',
  workerRef: { displayName: 'Tran T.H.', nationality: '베트남', maskLevel: 'masked' },
  channel: 'zalo',
  channelLabel: 'Zalo',
  caseId: 'tranCase',
  messages: [
    {
      messageId: 'tran-msg-out-1',
      threadId: 'tran',
      direction: 'out',
      channel: 'zalo',
      body: 'Chào anh Tran',
      lang: 'vi',
      at: '2026-07-01T09:20:00.000Z',
      deliveryStatus: 'sent',
      evidenceRef: '#4742',
      caseId: 'tranCase',
    },
    {
      messageId: 'tran-msg-in-1',
      threadId: 'tran',
      direction: 'in',
      channel: 'zalo',
      body: 'Hợp đồng lao động thì công ty đang giữ ạ.',
      lang: 'vi',
      at: '2026-07-04T10:12:00.000Z',
      caseId: 'tranCase',
    },
  ],
  interpretation: INTERPRETATION,
  interpretationStatus: 'pending_review',
  preview: '응답 도착 — AI 해석 준비됨 · 담당자 확인 필요',
  timeLabel: '10:12',
};

// InterpretationCard가 항상 useNextAction()(→useNavigate())을 호출하므로 Router 컨텍스트가 필요하다.
function renderScreen(state: ThreadViewState, overrides: Partial<Parameters<typeof ThreadScreen>[0]> = {}) {
  return render(
    <MemoryRouter>
      <ThreadScreen state={state} onConfirm={vi.fn()} {...overrides} />
    </MemoryRouter>,
  );
}

describe('ThreadScreen — 상태 5종', () => {
  it('default/interpretation: 원문은 접힌 상태로 시작하고 탭하면 펼쳐진다', () => {
    renderScreen({ status: 'default', mode: 'interpretation', thread: TRAN_THREAD, interpretation: INTERPRETATION });

    expect(screen.getByText('응답 도착 · Tran T.H.')).toBeInTheDocument();
    expect(screen.queryByText(/công ty đang giữ/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /원문/ }));
    expect(screen.getByText(/công ty đang giữ/)).toBeInTheDocument();

    expect(screen.getByText('담당자 확인 필요')).toBeInTheDocument();
    expect(screen.getByText('확인 전에는 상태가 확정되지 않습니다')).toBeInTheDocument();
  });

  it('default/interpretation: 상태 반영 확인 클릭 시 onConfirm이 호출된다', () => {
    const onConfirm = vi.fn();
    renderScreen(
      { status: 'default', mode: 'interpretation', thread: TRAN_THREAD, interpretation: INTERPRETATION },
      { onConfirm },
    );

    fireEvent.click(screen.getByRole('button', { name: '상태 반영 확인' }));
    expect(onConfirm).toHaveBeenCalledWith(['tran-doc-contract']);
  });

  it('default/timeline: 메시지 버블과 확인 완료 카드, 하단 초안 버튼을 렌더한다', () => {
    const confirmedThread: MessageThread = { ...TRAN_THREAD, interpretationStatus: 'confirmed' };
    const onNewDraft = vi.fn();
    renderScreen({ status: 'default', mode: 'timeline', thread: confirmedThread }, { onNewDraft });

    expect(screen.getByText('Chào anh Tran')).toBeInTheDocument();
    expect(screen.getByText(/công ty đang giữ/)).toBeInTheDocument();
    expect(screen.getByText('상태 반영 완료 — 계약서 회사 확인 · 여권 제출 대기 (판단 기록 #4791)')).toBeInTheDocument();
    expect(screen.getByText('모든 메시지는 승인 후에만 발송됩니다')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '새 메시지 초안 만들기' }));
    expect(onNewDraft).toHaveBeenCalled();
  });

  it('default/timeline: caseId가 없으면 초안 버튼이 비활성화된다', () => {
    const threadWithoutCase: MessageThread = { ...TRAN_THREAD };
    delete threadWithoutCase.caseId;
    renderScreen({ status: 'default', mode: 'timeline', thread: threadWithoutCase });

    expect(screen.getByRole('button', { name: '새 메시지 초안 만들기' })).toBeDisabled();
  });

  it('empty: 아직 응답이 없습니다 안내를 보여준다', () => {
    const emptyThread: MessageThread = { ...TRAN_THREAD, messages: [], interpretationStatus: 'none' };
    renderScreen({ status: 'empty', thread: emptyThread });

    expect(screen.getByText('아직 응답이 없습니다')).toBeInTheDocument();
  });

  it('loading: 원문 버블(원문 접근 버튼)은 즉시 렌더하고 요약 자리는 스켈레톤이다', () => {
    renderScreen({ status: 'loading', thread: TRAN_THREAD });

    // 원문 접근은 절대 막지 않는다 — 탭하면 즉시 펼쳐진다(해석 진행 중에도 차단되지 않음).
    fireEvent.click(screen.getByRole('button', { name: /원문/ }));
    expect(screen.getByText(/công ty đang giữ/)).toBeInTheDocument();
    expect(screen.getByText('AI가 응답을 해석하고 있습니다')).toBeInTheDocument();
  });

  it('error: 원문은 유지되고 다시 시도 버튼이 onRetry를 호출한다', () => {
    const onRetry = vi.fn();
    renderScreen({ status: 'error', thread: TRAN_THREAD }, { onRetry });

    // 요약 실패와 무관하게 원문 접근은 항상 가능해야 한다.
    fireEvent.click(screen.getByRole('button', { name: /원문/ }));
    expect(screen.getByText(/công ty đang giữ/)).toBeInTheDocument();
    expect(screen.getByText('요약에 실패했습니다')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(onRetry).toHaveBeenCalled();
  });

  it('offline: OfflineBanner와 캐시 요약을 보여주고 확인 버튼은 disabled다', () => {
    renderScreen({
      status: 'offline',
      thread: TRAN_THREAD,
      interpretation: INTERPRETATION,
      lastSyncedAt: '08:12',
    });

    expect(screen.getByText(/오프라인/)).toBeInTheDocument();
    expect(screen.getByText('오프라인 상태입니다 · 재연결 시 자동 동기화')).toBeInTheDocument();
    expect(screen.getByText(INTERPRETATION.summaryKo)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '상태 반영 확인' })).toBeDisabled();
  });
});
