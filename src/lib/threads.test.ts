import { describe, expect, it } from 'vitest';
import { THREADS } from '@/mocks/threads';
import type { MessageThread } from '@/types';
import { countArrivedResponses, sortThreads, threadBadge } from './threads';

function thread(overrides: Partial<MessageThread>): MessageThread {
  return {
    threadId: 'thread',
    workerRef: { displayName: 'Worker', nationality: '베트남', maskLevel: 'masked' },
    channel: 'zalo',
    channelLabel: 'Zalo',
    messages: [],
    interpretationStatus: 'none',
    preview: '요약',
    timeLabel: '오늘',
    ...overrides,
  };
}

describe('threadBadge', () => {
  it('응답 도착(pending_review)이면 최우선으로 approval 배지를 반환한다', () => {
    const t = thread({
      interpretationStatus: 'pending_review',
      draftCaseId: 'x',
      messages: [],
    });
    expect(threadBadge(t)).toEqual({ label: '응답 도착', tone: 'approval' });
  });

  it('draftCaseId가 있고 아직 메시지가 없으면 승인 대기(approval)를 반환한다', () => {
    const t = thread({ draftCaseId: 'nguyen', messages: [] });
    expect(threadBadge(t)).toEqual({ label: '승인 대기', tone: 'approval' });
  });

  it('interpretationStatus가 confirmed면 확인 완료(neutral)를 반환한다', () => {
    const t = thread({ interpretationStatus: 'confirmed' });
    expect(threadBadge(t)).toEqual({ label: '확인 완료', tone: 'neutral' });
  });

  it('마지막 out 메시지가 sent면 발송됨(positive)을 반환한다', () => {
    const t = thread({
      messages: [
        {
          messageId: 'm1',
          threadId: 'thread',
          direction: 'out',
          channel: 'sms',
          body: 'x',
          lang: 'mn',
          at: '2026-07-03T00:00:00.000Z',
          deliveryStatus: 'sent',
        },
      ],
    });
    expect(threadBadge(t)).toEqual({ label: '발송됨', tone: 'positive' });
  });

  it('그 외에는 초안(neutral)을 반환한다', () => {
    const t = thread({
      messages: [
        {
          messageId: 'm1',
          threadId: 'thread',
          direction: 'out',
          channel: 'sms',
          body: 'x',
          lang: 'mn',
          at: '2026-07-03T00:00:00.000Z',
          deliveryStatus: 'draft',
        },
      ],
    });
    expect(threadBadge(t)).toEqual({ label: '초안', tone: 'neutral' });
  });

  it('가장 최근 out 메시지 기준으로 판단한다(그 앞의 in 메시지는 무시)', () => {
    const t = thread({
      messages: [
        {
          messageId: 'm1',
          threadId: 'thread',
          direction: 'out',
          channel: 'sms',
          body: 'x',
          lang: 'mn',
          at: '2026-07-01T00:00:00.000Z',
          deliveryStatus: 'sent',
        },
        {
          messageId: 'm2',
          threadId: 'thread',
          direction: 'in',
          channel: 'sms',
          body: 'y',
          lang: 'mn',
          at: '2026-07-02T00:00:00.000Z',
        },
      ],
    });
    expect(threadBadge(t)).toEqual({ label: '발송됨', tone: 'positive' });
  });
});

describe('sortThreads', () => {
  it('응답 도착 스레드를 최상단 고정하고 나머지는 입력 순서를 유지한다', () => {
    const a = thread({ threadId: 'a' });
    const b = thread({ threadId: 'b', interpretationStatus: 'pending_review' });
    const c = thread({ threadId: 'c' });

    expect(sortThreads([a, b, c]).map((t) => t.threadId)).toEqual(['b', 'a', 'c']);
  });

  it('응답 도착 스레드가 여러 개면 서로의 상대 순서를 유지한다', () => {
    const a = thread({ threadId: 'a', interpretationStatus: 'pending_review' });
    const b = thread({ threadId: 'b' });
    const c = thread({ threadId: 'c', interpretationStatus: 'pending_review' });

    expect(sortThreads([a, b, c]).map((t) => t.threadId)).toEqual(['a', 'c', 'b']);
  });

  it('mocks/threads.ts THREADS에 적용하면 tran이 최상단으로 올라온다', () => {
    expect(sortThreads(THREADS).map((t) => t.threadId)).toEqual(['tran', 'nguyen', 'bayar']);
  });
});

describe('countArrivedResponses', () => {
  it('pending_review 스레드 개수를 센다', () => {
    expect(countArrivedResponses(THREADS)).toBe(1);
  });

  it('없으면 0을 반환한다', () => {
    expect(countArrivedResponses([thread({ threadId: 'a' })])).toBe(0);
  });
});
