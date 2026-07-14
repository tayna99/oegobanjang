import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Message } from '@/types';
import { MessageBubble } from './MessageBubble';

const OUT_MESSAGE: Message = {
  messageId: 'm-out',
  threadId: 'tran',
  direction: 'out',
  channel: 'zalo',
  body: 'Chào anh Tran',
  lang: 'vi',
  at: '2026-07-01T09:20:00.000Z',
  deliveryStatus: 'sent',
  evidenceRef: '#4742',
  caseId: 'tranCase',
};

const IN_MESSAGE: Message = {
  messageId: 'm-in',
  threadId: 'tran',
  direction: 'in',
  channel: 'zalo',
  body: 'Hợp đồng lao động thì công ty đang giữ ạ.',
  lang: 'vi',
  at: '2026-07-04T10:12:00.000Z',
};

describe('MessageBubble', () => {
  it('out 메시지는 우측 정렬 메타에 v3 형식 캡션을 표시한다', () => {
    render(<MessageBubble message={OUT_MESSAGE} />);
    expect(screen.getByText('Chào anh Tran')).toBeInTheDocument();
    expect(screen.getByText('승인 후 발송됨 · 판단 기록 #4742 · 09:20')).toBeInTheDocument();
  });

  it('in 메시지는 수신 시각 · 수신 메타를 표시한다', () => {
    render(<MessageBubble message={IN_MESSAGE} />);
    expect(screen.getByText(/công ty đang giữ/)).toBeInTheDocument();
    expect(screen.getByText('10:12 · 수신')).toBeInTheDocument();
  });
});
