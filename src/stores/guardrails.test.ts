import { beforeEach, describe, expect, it } from 'vitest';
import { GuardrailError } from '@/lib/guardrail';
import { useApprovalStore } from './approvalStore';
import { useCaseStore } from './caseStore';
import { useEvidenceStore } from './evidenceStore';
import type { CaseCard, EvidenceEvent } from '@/types';

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
});

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

describe('가드레일 보강 — 해석 확인 문서 갱신(caseStore.applyInterpretationUpdates)', () => {
  it('갱신은 CaseState를 바꾸지 않고 docUpdates 네임스페이스에만 쌓인다', () => {
    seedCase('risk_review');
    useCaseStore.getState().applyInterpretationUpdates('c1', [{ field: '표준근로계약서', to: '회사 확인 필요' }]);
    expect(useCaseStore.getState().cases['c1'].state).toBe('risk_review');
    expect(useCaseStore.getState().docUpdates['c1']?.['표준근로계약서']).toEqual({ to: '회사 확인 필요' });
  });

  it('같은 필드를 다시 갱신하면 최신값으로 덮어쓴다', () => {
    seedCase('risk_review');
    const store = useCaseStore.getState();
    store.applyInterpretationUpdates('c1', [{ field: '여권 사본', to: '제출 예정 · 내일' }]);
    store.applyInterpretationUpdates('c1', [{ field: '여권 사본', to: '확보' }]);
    expect(useCaseStore.getState().docUpdates['c1']?.['여권 사본']).toEqual({ to: '확보' });
  });
});

describe('가드레일 5 — 발송 함수 부재 (caseStore)', () => {
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
