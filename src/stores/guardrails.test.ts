import { beforeEach, describe, expect, it } from 'vitest';
import { GuardrailError } from '@/lib/guardrail';
import { useApprovalStore } from './approvalStore';
import { useCaseStore } from './caseStore';
import { useEvidenceStore } from './evidenceStore';
import { useThreadStore } from './threadStore';
import { THREADS } from '@/mocks/threads';
import type { CaseCard, EvidenceEvent, Interpretation, MessageThread } from '@/types';

const action = (id: string) => id;

function seedCase(state: CaseCard['state']): CaseCard {
  const card: CaseCard = {
    caseId: 'c1',
    caseCode: 'case_test',
    title: '테스트 케이스',
    severity: 'HIGH',
    state,
    approvalRequired: true,
    primaryAction: {
      actionId: 'a1',
      label: '보내기 승인',
      state: 'ready',
      requiresApproval: true,
      kind: 'approve',
    },
    secondaryAction: {
      actionId: 'a2',
      label: '초안 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'draft',
    },
    preparedBy: 'rule',
  };
  useCaseStore.getState().upsert(card);
  return card;
}

beforeEach(() => {
  useApprovalStore.getState().reset();
  useCaseStore.getState().reset();
  useEvidenceStore.getState().reset();
  useThreadStore.getState().reset();
});

function seedThread(
  interpretationStatus: MessageThread['interpretationStatus'],
  interpretation?: Interpretation,
): MessageThread {
  const thread: MessageThread = {
    threadId: 't1',
    workerRef: { displayName: '테스트 W.', nationality: '베트남', maskLevel: 'masked' },
    channel: 'zalo',
    channelLabel: 'Zalo',
    caseId: 'c1',
    messages: [],
    interpretation,
    interpretationStatus,
    preview: '초기 미리보기',
    timeLabel: '오늘',
  };
  useThreadStore.getState().upsert(thread);
  return thread;
}

const baseInterpretation: Interpretation = {
  interpretationId: 'i1',
  threadId: 't1',
  caseId: 'c1',
  summaryKo: '테스트 요약',
  confidence: 'high',
  updates: [
    { updateId: 'u1', field: '표준근로계약서', from: '누락', to: '회사 확인 필요', badgeTone: 'warning' },
  ],
  recommendedActions: [],
  isFinal: false,
  confirmedSummary: '확인된 요약 문구',
  confirmedCardText: '확정 카드 문구',
  evidenceRef: '#9999',
};

describe('가드레일 1 — 승인 없이 dispatch 불가', () => {
  it('승인 요청만 있고 승인 전이면 dispatch가 GuardrailError', () => {
    const store = useApprovalStore.getState();
    store.requestApproval(action('a1'));
    expect(() => store.dispatch('a1')).toThrow(GuardrailError);
  });

  it('요청조차 없는 액션 dispatch도 차단', () => {
    expect(() => useApprovalStore.getState().dispatch('nope')).toThrow(
      GuardrailError,
    );
  });

  it('승인 후에만 dispatch가 mock 경계까지 통과', () => {
    const store = useApprovalStore.getState();
    store.requestApproval('a1');
    store.decide('a1', 'approved', 'key-1');
    expect(useApprovalStore.getState().dispatch('a1')).toEqual({
      dispatched: true,
      actionId: 'a1',
    });
  });

  it('rejected면 dispatch 차단', () => {
    const store = useApprovalStore.getState();
    store.requestApproval('a1');
    store.decide('a1', 'rejected', 'key-1');
    expect(() => useApprovalStore.getState().dispatch('a1')).toThrow(
      GuardrailError,
    );
  });
});

describe('가드레일 2 — evidence append-only', () => {
  const evt = (id: string): EvidenceEvent => ({
    id,
    type: 'approval_requested',
    at: '2026-07-06T00:00:00.000Z',
  });

  it('append만으로 누적되고 기존 이벤트는 보존된다', () => {
    const store = useEvidenceStore.getState();
    store.append(evt('e1'));
    store.append(evt('e2'));
    const events = useEvidenceStore.getState().events;
    expect(events.map((e) => e.id)).toEqual(['e1', 'e2']);
  });

  it('스토어에 수정·삭제 액션이 존재하지 않는다', () => {
    const store = useEvidenceStore.getState() as unknown as Record<
      string,
      unknown
    >;
    expect(store.update).toBeUndefined();
    expect(store.remove).toBeUndefined();
    expect(store.delete).toBeUndefined();
    expect(store.splice).toBeUndefined();
  });

  it('append된 이벤트는 동결되어 사후 변형이 무시된다', () => {
    useEvidenceStore.getState().append(evt('e1'));
    const stored = useEvidenceStore.getState().events[0];
    expect(() => {
      // 런타임 동결 검증: ESM strict 모드에서 frozen 객체 쓰기는 throw.
      stored.type = 'final_response_generated';
    }).toThrow();
    expect(useEvidenceStore.getState().events[0].type).toBe(
      'approval_requested',
    );
  });
});

describe('가드레일 3 — 중복 승인 차단', () => {
  it('요청 단계에는 결정 idempotencyKey를 만들지 않는다', () => {
    const approval = useApprovalStore.getState().requestApproval('a1');
    expect(approval.idempotencyKey).toBeNull();
  });

  it('결정에는 비어 있지 않은 idempotencyKey가 필요하다', () => {
    const store = useApprovalStore.getState();
    store.requestApproval('a1');
    expect(() => store.decide('a1', 'approved', '   ')).toThrow(GuardrailError);
  });

  it('같은 idempotencyKey로 두 번 decide하면 두 번째는 no-op', () => {
    const store = useApprovalStore.getState();
    store.requestApproval('a1');
    const first = store.decide('a1', 'approved', 'key-1');
    expect(first.status).toBe('approved');

    // 두 번째: rejected로 뒤집으려 해도 같은 키라 무시된다.
    const second = useApprovalStore
      .getState()
      .decide('a1', 'rejected', 'key-1');
    expect(second.status).toBe('approved');
    expect(useApprovalStore.getState().approvals['a1'].status).toBe('approved');
  });

  it('이미 결정된 액션을 다른 키로 다시 결정하려 하면 차단', () => {
    const store = useApprovalStore.getState();
    store.requestApproval('a1');
    store.decide('a1', 'approved', 'key-1');
    expect(() =>
      useApprovalStore.getState().decide('a1', 'rejected', 'key-2'),
    ).toThrow(GuardrailError);
  });
});

describe('가드레일 보강 — Case 상태 전이', () => {
  it('정상 경로 전이는 허용', () => {
    seedCase('draft');
    const { transition } = useCaseStore.getState();
    transition('c1', 'risk_review');
    transition('c1', 'approval_pending');
    transition('c1', 'human_approved');
    transition('c1', 'completed');
    expect(useCaseStore.getState().cases['c1'].state).toBe('completed');
  });

  it('순서 밖 전이는 GuardrailError', () => {
    seedCase('draft');
    expect(() =>
      useCaseStore.getState().transition('c1', 'human_approved'),
    ).toThrow(GuardrailError);
  });

  it('completed는 종착 — 추가 전이 불가', () => {
    seedCase('completed');
    expect(() =>
      useCaseStore.getState().transition('c1', 'risk_review'),
    ).toThrow(GuardrailError);
  });

  it('반려(returned) 왕복 — 승인 대기↔반려만 허용 (Mobile §2c, 2.5.4b)', () => {
    seedCase('approval_pending');
    const { transition } = useCaseStore.getState();
    transition('c1', 'returned');
    expect(useCaseStore.getState().cases['c1'].state).toBe('returned');
    transition('c1', 'approval_pending');
    expect(useCaseStore.getState().cases['c1'].state).toBe('approval_pending');
    // returned에서 승인/완료로 건너뛰기는 불가.
    useCaseStore.getState().transition('c1', 'returned');
    expect(() => useCaseStore.getState().transition('c1', 'human_approved')).toThrow(GuardrailError);
  });
});

describe('가드레일 보강 — 반려 사유·케이스 단위 승인 (2.5.4b)', () => {
  it('반려 시 사유가 승인 기록에 남는다 ("반려 시 사유가 판단 기록에 남고 …" Mobile §2c)', () => {
    const store = useApprovalStore.getState();
    store.requestApproval('a1');
    const rejected = store.decide('a1', 'rejected', 'key-1', '근거 문서 최신성 확인 필요');
    expect(rejected.status).toBe('rejected');
    expect(rejected.reason).toBe('근거 문서 최신성 확인 필요');
  });

  it('승인은 액션 단위 API만 존재한다 — 일괄 승인 금지 (PC §3a "승인은 케이스 단위로만" 비준)', () => {
    const store = useApprovalStore.getState() as unknown as Record<string, unknown>;
    expect(store.decideAll).toBeUndefined();
    expect(store.approveAll).toBeUndefined();
    expect(store.batchDecide).toBeUndefined();
  });
});

describe('가드레일 4 — 해석 확인(threadStore.confirmInterpretation)', () => {
  it("pending_review가 아닌 스레드('none')에서 호출하면 GuardrailError", () => {
    seedThread('none');
    expect(() =>
      useThreadStore.getState().confirmInterpretation('t1', []),
    ).toThrow(GuardrailError);
  });

  it("해석 자체가 없는데 확인하려는 경우도 GuardrailError('none' + interpretation 없음)", () => {
    seedThread('none', undefined);
    expect(() =>
      useThreadStore.getState().confirmInterpretation('t1', []),
    ).toThrow(GuardrailError);
  });

  it('confirmed 스레드에 재호출하면 에러 없이 동일 interpretation을 반환하는 no-op', () => {
    seedThread('confirmed', baseInterpretation);
    const result = useThreadStore.getState().confirmInterpretation('t1', []);
    expect(result).toEqual(baseInterpretation);
    expect(useThreadStore.getState().threads['t1'].interpretationStatus).toBe(
      'confirmed',
    );
  });

  it('성공 케이스: 전체 updateId를 정확히 담으면 pending_review → confirmed 전이 및 preview 갱신', () => {
    seedThread('pending_review', baseInterpretation);
    const result = useThreadStore.getState().confirmInterpretation('t1', ['u1']);
    expect(result).toEqual(baseInterpretation);

    const updated = useThreadStore.getState().threads['t1'];
    expect(updated.interpretationStatus).toBe('confirmed');
    expect(updated.preview).toBe(baseInterpretation.confirmedSummary);
  });

  // 유효성·원자성 — updateIds를 무시하던 이전 구현은 어떤 입력을 넣어도 무조건 커밋됐다.
  // 아래 두 테스트는 검증을 통과하지 못하면 어떤 스토어도 갱신되지 않음을 확인한다.
  it('빈 updateIds는 GuardrailError — 스레드 상태가 바뀌지 않는다', () => {
    seedThread('pending_review', baseInterpretation);
    expect(() =>
      useThreadStore.getState().confirmInterpretation('t1', []),
    ).toThrow(GuardrailError);
    expect(useThreadStore.getState().threads['t1'].interpretationStatus).toBe(
      'pending_review',
    );
  });

  it('중복 updateId는 GuardrailError — 각 업데이트를 정확히 한 번씩 확인해야 한다', () => {
    const interpretation = {
      ...baseInterpretation,
      updates: [baseInterpretation.updates[0], { ...baseInterpretation.updates[0], updateId: 'u2' }],
    };
    seedThread('pending_review', interpretation);

    expect(() =>
      useThreadStore.getState().confirmInterpretation('t1', ['u1', 'u1', 'u2']),
    ).toThrow(GuardrailError);
    expect(useThreadStore.getState().threads.t1.interpretationStatus).toBe('pending_review');
  });

  it('존재하지 않는 updateId가 섞이면 GuardrailError — 부분 일치도 거부한다', () => {
    seedThread('pending_review', baseInterpretation);
    expect(() =>
      useThreadStore.getState().confirmInterpretation('t1', ['u1', 'bogus-id']),
    ).toThrow(GuardrailError);
    expect(useThreadStore.getState().threads['t1'].interpretationStatus).toBe(
      'pending_review',
    );
  });
});

describe('가드레일 5 — 발송 함수 부재 (threadStore·caseStore)', () => {
  it('threadStore에 sendMessage/dispatch 계열 함수가 정의되어 있지 않다', () => {
    const store = useThreadStore.getState() as unknown as Record<
      string,
      unknown
    >;
    expect(store.sendMessage).toBeUndefined();
    expect(store.dispatchMessage).toBeUndefined();
    expect(store.send).toBeUndefined();
    expect(store.dispatch).toBeUndefined();
  });

  it('caseStore에 sendMessage/dispatch 계열 함수가 정의되어 있지 않다', () => {
    const store = useCaseStore.getState() as unknown as Record<
      string,
      unknown
    >;
    expect(store.sendMessage).toBeUndefined();
    expect(store.dispatchMessage).toBeUndefined();
    expect(store.send).toBeUndefined();
    expect(store.dispatch).toBeUndefined();
  });
});

describe('THREADS 픽스처 — 해석 미확정 불변', () => {
  it('모든 interpretation.isFinal이 정확히 false다', () => {
    const withInterpretation = THREADS.filter((t) => t.interpretation);
    expect(withInterpretation.length).toBeGreaterThan(0);
    for (const thread of withInterpretation) {
      expect(thread.interpretation?.isFinal).toBe(false);
    }
  });
});
