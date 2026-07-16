// 메시지 탭 스레드 리스트 순수 셀렉터 — 탭별기획 §3.2 "상태 배지 우선순위",
// §3.4 "응답 도착 스레드는 리스트 최상단 고정". 정렬·배지 계산은 여기 한 곳에만
// (rules/frontend.md "파생값은 selector로 — 컴포넌트에서 정렬·필터 로직 재구현 금지").
import type { BadgeTone } from './badgeTone';
import type { Message, MessageThread } from '@/types';

export interface ThreadBadge {
  label: string;
  tone: BadgeTone;
}

// 우선순위(탭별기획 §3.2): 응답 도착(info) > 승인 대기(pending) > 발송됨(success) > 초안(neutral).
// '확인 완료'는 응답 해석을 확인한 뒤(interpretationStatus:'confirmed')의 후속 상태.
export function threadBadge(thread: MessageThread): ThreadBadge {
  if (thread.interpretationStatus === 'pending_review') {
    return { label: '응답 도착', tone: 'info' };
  }

  if (thread.draftCaseId && thread.messages.length === 0) {
    return { label: '승인 대기', tone: 'pending' };
  }

  if (thread.interpretationStatus === 'confirmed') {
    return { label: '확인 완료', tone: 'neutral' };
  }

  let lastOutStatus: MessageThread['messages'][number]['deliveryStatus'];
  for (let i = thread.messages.length - 1; i >= 0; i -= 1) {
    const message = thread.messages[i];
    if (message.direction === 'out') {
      lastOutStatus = message.deliveryStatus;
      break;
    }
  }
  if (lastOutStatus === 'sent') {
    return { label: '발송됨', tone: 'success' };
  }

  return { label: '초안', tone: 'neutral' };
}

// 응답 도착(pending_review) 스레드를 최상단 고정, 나머지는 입력 순서 그대로 유지.
// 시각 계산 없이 결정적(GOTCHAS §4 "시간·정렬은 deterministic").
export function sortThreads(threads: MessageThread[]): MessageThread[] {
  const arrived: MessageThread[] = [];
  const rest: MessageThread[] = [];
  for (const thread of threads) {
    if (thread.interpretationStatus === 'pending_review') {
      arrived.push(thread);
    } else {
      rest.push(thread);
    }
  }
  return [...arrived, ...rest];
}

export function countArrivedResponses(threads: MessageThread[]): number {
  return threads.filter((thread) => thread.interpretationStatus === 'pending_review').length;
}

// 스레드 상세(M6/타임라인) 시각 표기 — UTC 기준으로 고정해 실행 타임존과 무관하게
// deterministic하다(GOTCHAS §4 "시간 의존 테스트는 기준일 주입"과 같은 원칙).
// mocks/threads.ts의 at 값은 v3 원본 주석의 "09:20" 등 표시 시각과 UTC 시·분이 그대로 맞도록 넣어뒀다.
export function formatClockTime(iso: string): string {
  const date = new Date(iso);
  const hh = String(date.getUTCHours()).padStart(2, '0');
  const mm = String(date.getUTCMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export function formatDateCaption(iso: string): string {
  const date = new Date(iso);
  return `${date.getUTCMonth() + 1}월 ${date.getUTCDate()}일`;
}

// 타임라인 모드 원문 카드 — 스레드의 가장 최근 수신(in) 메시지. 없으면 undefined
// (아직 응답이 없는 스레드 = empty 상태).
export function latestInboundMessage(thread: MessageThread): Message | undefined {
  for (let i = thread.messages.length - 1; i >= 0; i -= 1) {
    if (thread.messages[i].direction === 'in') return thread.messages[i];
  }
  return undefined;
}
