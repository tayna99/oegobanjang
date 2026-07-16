import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { MessageThread } from '@/types';
import { ThreadListItem } from './ThreadListItem';

const BAYAR: MessageThread = {
  threadId: 'bayar',
  workerRef: { displayName: 'Bayar M.', nationality: '몽골', maskLevel: 'masked' },
  channel: 'sms',
  channelLabel: 'SMS',
  caseId: 'bayar',
  messages: [
    {
      messageId: 'bayar-msg-out-1',
      threadId: 'bayar',
      direction: 'out',
      channel: 'sms',
      body: '건강검진 일정 확인 요청',
      lang: 'mn',
      at: '2026-07-03T15:40:00.000Z',
      deliveryStatus: 'sent',
    },
  ],
  interpretationStatus: 'none',
  preview: '건강검진 일정 안내 — 발송 승인 완료 · 응답 대기',
  timeLabel: '어제',
  reminderScheduledLabel: '리마인드 7.6 예정',
};

describe('ThreadListItem', () => {
  it('이니셜 아바타, 이름, 국적·채널, 미리보기, 배지를 렌더한다', () => {
    render(<ThreadListItem thread={BAYAR} onOpen={vi.fn()} />);

    expect(screen.getByText('B')).toBeInTheDocument();
    expect(screen.getByText('Bayar M.')).toBeInTheDocument();
    expect(screen.getByText('몽골 · SMS')).toBeInTheDocument();
    expect(screen.getByText('건강검진 일정 안내 — 발송 승인 완료 · 응답 대기')).toBeInTheDocument();
    expect(screen.getByText('발송됨')).toBeInTheDocument();
  });

  it('reminderScheduledLabel이 있으면 시각 대신 리마인드 라벨을 보여준다', () => {
    render(<ThreadListItem thread={BAYAR} onOpen={vi.fn()} />);

    expect(screen.getByText('리마인드 7.6 예정')).toBeInTheDocument();
    expect(screen.queryByText('어제')).not.toBeInTheDocument();
  });

  it('탭하면 onOpen이 호출된다', () => {
    const onOpen = vi.fn();
    render(<ThreadListItem thread={BAYAR} onOpen={onOpen} />);

    fireEvent.click(screen.getByRole('button', { name: 'Bayar M.' }));
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it('interactive=false면 버튼이 아니라 읽기 전용 행으로 렌더한다', () => {
    const onOpen = vi.fn();
    render(<ThreadListItem thread={BAYAR} onOpen={onOpen} interactive={false} />);

    expect(screen.queryByRole('button', { name: 'Bayar M.' })).not.toBeInTheDocument();
    expect(screen.getByText('Bayar M.')).toBeInTheDocument();
  });
});
