import { create } from 'zustand';
import type { Interpretation, Message, MessageThread } from '@/types';
import { GuardrailError } from '@/lib/guardrail';
import { formatClockTime } from '@/lib/threads';

interface ThreadStoreState {
  threads: Record<string, MessageThread>;
  upsert: (thread: MessageThread) => void;
  /**
   * 응답 해석 확인 — pending_review에서만 진행 가능한 담당자 승인 경계.
   * updateIds는 interpretation.updates의 updateId 전체와 정확히 일치해야 한다(순서 무관,
   * 부분 확인은 이 데이터 모델에 없다 — interpretationStatus가 해석 전체에 걸리는 단일
   * 스칼라이기 때문). 이 검증을 통과하기 전에는 어떤 스토어도 갱신되지 않는다 —
   * ThreadPage.handleConfirm이 이어서 호출하는 caseStore.applyInterpretationUpdates·
   * evidenceStore.append는 예외를 던질 조건이 없는 순수 병합/추가이므로, 이 함수의
   * 검증-후-커밋 순서가 사실상 3개 스토어 갱신 전체의 원자성 경계가 된다.
   * 발송 함수는 여기 두지 않는다. sendMessage/dispatchMessage 등은 이 스토어에
   * 정의되지 않는다 — 승인은 상태(interpretationStatus)를 confirmed로 옮길 뿐,
   * 실제 채널 발송(mock dispatch 경계 포함)은 approvalStore.dispatch의 몫이다.
   */
  confirmInterpretation: (
    threadId: string,
    updateIds: string[],
  ) => Interpretation;
  /**
   * 인바운드 정규화 지점(MESSAGING_CHANNELS §3) — 근로자 응답 링크(R3.2)·(후속) webhook이
   * 여기로 합류한다. direction/channel/caseId는 스레드에서 파생해 스토어가 조립한다(호출자가
   * 위조 불가). preview는 상태 요약 고정 문자열만 — 원문(body)이 preview로 새는 경로를
   * 구조적으로 차단한다(GOTCHAS §3, src/lib/api/threads.ts의 real API 어댑터와 동일 문구
   * 재사용). interpretationStatus를 'pending_review'로 옮길 뿐 interpretation 객체는 만들지
   * 않는다 — mock 세계에는 해석 생성 에이전트(R4.5)가 없다. ThreadPage/MessagesWorkbench는
   * interpretation 부재 시 타임라인 모드로 렌더한다(기존 분기 그대로, "해석 확인" UI
   * 미노출 — 가짜 확인 흐름을 만들지 않는다). 같은 messageId 재수신은 no-op(evidenceStore.append와
   * 동일한 멱등 규칙).
   */
  receiveInbound: (
    threadId: string,
    inbound: { messageId: string; body: string; lang: string; at: string },
  ) => void;
  /** 테스트용 초기화 — evidenceStore.ts의 reset 선례. */
  reset: () => void;
}

export const useThreadStore = create<ThreadStoreState>((set, get) => ({
  threads: {},

  upsert: (thread) =>
    set((s) => ({ threads: { ...s.threads, [thread.threadId]: thread } })),

  confirmInterpretation: (threadId, updateIds) => {
    const thread = get().threads[threadId];
    if (!thread) {
      throw new GuardrailError(`존재하지 않는 스레드: ${threadId}`);
    }

    // 이미 확인된 해석에 재호출 — 에러 없이 기존 interpretation을 그대로 반환하는 no-op
    // (approvalStore.decide의 idempotency 처리와 같은 정신이되, 여기서는 상태 자체가
    // 멱등성 판단 기준이므로 별도의 idempotencyKey 파라미터가 필요 없다). 이미 커밋된
    // 결과를 그대로 돌려줄 뿐이라 updateIds를 다시 검증하지 않는다 — 이중 클릭 재호출까지
    // 이 조건으로 막힌다.
    if (thread.interpretationStatus === 'confirmed') {
      if (!thread.interpretation) {
        throw new GuardrailError(`확인할 해석이 없는 스레드: ${threadId}`);
      }
      return thread.interpretation;
    }

    // 'none'(해석 자체가 없음)도 여기서 함께 걸러진다.
    if (thread.interpretationStatus !== 'pending_review' || !thread.interpretation) {
      throw new GuardrailError(
        `pending_review 상태에서만 해석 확인 가능: 현재 ${thread.interpretationStatus}`,
      );
    }

    const interpretation = thread.interpretation;

    // updateIds 전수 검증 — 이 시점까지 어떤 스토어도 갱신되지 않았다. 빈 배열이나
    // 존재하지 않는 id, 일부만 담긴 목록은 전부 거부한다(부분 확인은 이 데이터 모델에
    // 없다). field 문자열을 id로 재사용하던 이전 구현은 이 검증이 없어 어떤 입력을
    // 넣어도 무조건 커밋됐다 — 여기서 막는다.
    const validIds = interpretation.updates.map((u) => u.updateId);
    const providedSet = new Set(updateIds);
    const missing = validIds.filter((id) => !providedSet.has(id));
    const unknown = updateIds.filter((id) => !validIds.includes(id));
    const hasDuplicate = providedSet.size !== updateIds.length;
    if (
      updateIds.length !== validIds.length ||
      hasDuplicate ||
      missing.length > 0 ||
      unknown.length > 0
    ) {
      throw new GuardrailError(
        `해석의 모든 업데이트를 정확히 확인해야 합니다: 기대 [${validIds.join(', ')}], 받음 [${updateIds.join(', ')}]`,
      );
    }

    set((s) => ({
      threads: {
        ...s.threads,
        [threadId]: {
          ...thread,
          interpretationStatus: 'confirmed',
          preview: interpretation.confirmedSummary ?? thread.preview,
        },
      },
    }));
    return interpretation;
  },

  receiveInbound: (threadId, inbound) => {
    const thread = get().threads[threadId];
    if (!thread) {
      throw new GuardrailError(`존재하지 않는 스레드: ${threadId}`);
    }
    if (thread.messages.some((m) => m.messageId === inbound.messageId)) {
      return; // 중복 수신 — no-op(멱등)
    }

    const message: Message = {
      messageId: inbound.messageId,
      threadId,
      direction: 'in',
      channel: thread.channel,
      body: inbound.body,
      lang: inbound.lang,
      at: inbound.at,
      caseId: thread.caseId,
    };

    set((s) => ({
      threads: {
        ...s.threads,
        [threadId]: {
          ...thread,
          messages: [...thread.messages, message],
          preview: '응답이 도착했습니다', // src/lib/api/threads.ts의 real API 상태 요약과 동일 문구 재사용
          timeLabel: formatClockTime(inbound.at),
          interpretationStatus: 'pending_review',
        },
      },
    }));
  },

  reset: () => set({ threads: {} }),
}));
