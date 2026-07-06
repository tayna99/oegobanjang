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
});
