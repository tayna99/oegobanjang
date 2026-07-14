import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { MessageThread } from '@/types';
import { MessagesScreen } from './MessagesScreen';

const NGUYEN: MessageThread = {
  threadId: 'nguyen',
  workerRef: { displayName: 'Nguyen V.', nationality: '베트남', maskLevel: 'masked' },
  channel: 'zalo',
  channelLabel: 'Zalo',
  draftCaseId: 'nguyen',
  messages: [],
  interpretationStatus: 'none',
  preview: '서류 요청 초안 — 표준근로계약서·여권 사본',
  timeLabel: '오늘',
};

const TRAN: MessageThread = {
  threadId: 'tran',
  workerRef: { displayName: 'Tran T.H.', nationality: '베트남', maskLevel: 'masked' },
  channel: 'zalo',
  channelLabel: 'Zalo',
  caseId: 'tranCase',
  messages: [
    {
      messageId: 'tran-msg-in-1',
      threadId: 'tran',
      direction: 'in',
      channel: 'zalo',
      body: '원문은 여기에만 있어야 한다',
      lang: 'vi',
      at: '2026-07-04T10:12:00.000Z',
    },
  ],
  interpretationStatus: 'pending_review',
  preview: '응답 도착 — AI 해석 준비됨 · 담당자 확인 필요',
  timeLabel: '10:12',
};

function renderScreen(state: Parameters<typeof MessagesScreen>[0]['state']) {
  return render(
    <MessagesScreen
      state={state}
      onOpenThread={vi.fn()}
      onStartFromCases={vi.fn()}
      onRetry={vi.fn()}
    />,
  );
}

describe('MessagesScreen — 상태 5종', () => {
  it('default: 앱바·정렬된 행·하단 고정 캡션을 렌더한다', () => {
    renderScreen({ status: 'default', threads: [TRAN, NGUYEN] });

    expect(screen.getByRole('heading', { name: '메시지' })).toBeInTheDocument();
    expect(screen.getByText('컨택 2건')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tran T.H.' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nguyen V.' })).toBeInTheDocument();
    expect(screen.getByText('모든 메시지는 승인 후에만 발송됩니다')).toBeInTheDocument();
  });

  it('default: 배지 라벨이 우선순위대로 렌더된다', () => {
    renderScreen({ status: 'default', threads: [TRAN, NGUYEN] });

    expect(screen.getByText('응답 도착')).toBeInTheDocument();
    expect(screen.getByText('승인 대기')).toBeInTheDocument();
  });

  it('default: 행 탭 시 onOpenThread가 해당 스레드로 호출된다', () => {
    const onOpenThread = vi.fn();
    render(
      <MessagesScreen
        state={{ status: 'default', threads: [NGUYEN] }}
        onOpenThread={onOpenThread}
        onStartFromCases={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Nguyen V.' }));
    expect(onOpenThread).toHaveBeenCalledWith(NGUYEN);
  });

  it('empty: 빈 상태 안내 문구와 케이스에서 시작하기 버튼을 보여준다', () => {
    const onStartFromCases = vi.fn();
    render(
      <MessagesScreen state={{ status: 'empty' }} onOpenThread={vi.fn()} onStartFromCases={onStartFromCases} />,
    );

    expect(screen.getByText('아직 컨택 이력이 없습니다')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '케이스에서 시작하기' }));
    expect(onStartFromCases).toHaveBeenCalled();
  });

  it('loading: 스켈레톤 3행을 보여주고 실제 행은 렌더하지 않는다', () => {
    renderScreen({ status: 'loading' });

    expect(screen.getByRole('heading', { name: '메시지' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Nguyen V.' })).not.toBeInTheDocument();
  });

  it('error: 원인 1줄과 다시 시도 버튼을 보여준다', () => {
    const onRetry = vi.fn();
    render(
      <MessagesScreen
        state={{ status: 'error' }}
        onOpenThread={vi.fn()}
        onStartFromCases={vi.fn()}
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText('메시지를 불러오지 못했습니다')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(onRetry).toHaveBeenCalled();
  });

  it('offline: 오프라인 배너와 캐시 리스트를 읽기 전용으로 보여준다', () => {
    renderScreen({ status: 'offline', cachedThreads: [TRAN], lastSyncedAt: '08:12' });

    expect(screen.getByText(/오프라인/)).toBeInTheDocument();
    expect(screen.getByText('오프라인 상태입니다 · 재연결 시 자동 동기화')).toBeInTheDocument();
    expect(screen.getByText('Tran T.H.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Tran T.H.' })).not.toBeInTheDocument();
  });

  it('원문 메시지 문자열이 DOM에 노출되지 않는다(PII 가드)', () => {
    renderScreen({ status: 'default', threads: [TRAN] });
    expect(screen.queryByText(/원문은 여기에만 있어야 한다/)).not.toBeInTheDocument();
  });
});
