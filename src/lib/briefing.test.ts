import { describe, expect, it } from 'vitest';
import { greetingText, sortCards, visibleCardsForRole } from './briefing';
import type { CaseCard } from '@/types';

function card(overrides: Partial<CaseCard>): CaseCard {
  return {
    caseId: 'x',
    title: 't',
    severity: 'LOW',
    state: 'draft',
    approvalRequired: false,
    primaryAction: { actionId: 'a', label: 'l', state: 'ready', requiresApproval: false, kind: 'detail' },
    secondaryAction: { actionId: 'b', label: 'l2', state: 'ready', requiresApproval: false, kind: 'detail' },
    preparedBy: 'rule',
    ...overrides,
  };
}

describe('greetingText', () => {
  it('manager는 담당자님 호칭을 쓴다', () => {
    expect(greetingText('manager', 3)).toBe('담당자님, 오늘 확인이 필요한 업무가 3건 있습니다.');
  });

  it('owner는 대표님 호칭을 쓴다', () => {
    expect(greetingText('owner', 1)).toBe('대표님, 오늘 확인이 필요한 업무가 1건 있습니다.');
  });

  it('0건이면 완료 문구를 쓴다', () => {
    expect(greetingText('manager', 0)).toBe('오늘 승인할 업무가 없습니다.');
  });
});

describe('sortCards — deterministic severity → dDay → id', () => {
  it('severity 순서(CRITICAL > HIGH > MEDIUM > LOW)로 정렬한다', () => {
    const cards = [card({ caseId: 'low', severity: 'LOW' }), card({ caseId: 'crit', severity: 'CRITICAL' }), card({ caseId: 'high', severity: 'HIGH' })];
    expect(sortCards(cards).map((c) => c.caseId)).toEqual(['crit', 'high', 'low']);
  });

  it('severity가 같으면 dDay 오름차순(더 급한 것 먼저)으로 정렬한다', () => {
    const cards = [
      card({ caseId: 'a', severity: 'HIGH', dDay: 30 }),
      card({ caseId: 'b', severity: 'HIGH', dDay: -3 }),
      card({ caseId: 'c', severity: 'HIGH', dDay: 5 }),
    ];
    expect(sortCards(cards).map((c) => c.caseId)).toEqual(['b', 'c', 'a']);
  });

  it('severity·dDay가 같으면 caseId 알파벳 순으로 정렬한다(deterministic tie-break)', () => {
    const cards = [card({ caseId: 'zeta', severity: 'LOW' }), card({ caseId: 'alpha', severity: 'LOW' })];
    expect(sortCards(cards).map((c) => c.caseId)).toEqual(['alpha', 'zeta']);
  });

  it('dDay가 없는 카드는 있는 카드보다 뒤로 간다', () => {
    const cards = [card({ caseId: 'nodday' }), card({ caseId: 'hasday', dDay: 10 })];
    expect(sortCards(cards).map((c) => c.caseId)).toEqual(['hasday', 'nodday']);
  });
});

describe('visibleCardsForRole', () => {
  const cards = [
    card({ caseId: 'need-approval', approvalRequired: true }),
    card({ caseId: 'just-review', approvalRequired: false }),
  ];

  it('owner는 승인 필요 카드만 본다', () => {
    expect(visibleCardsForRole(cards, 'owner').map((c) => c.caseId)).toEqual(['need-approval']);
  });

  it('manager는 전부 본다(승인 + 확인 필요)', () => {
    expect(visibleCardsForRole(cards, 'manager').map((c) => c.caseId)).toEqual(['need-approval', 'just-review']);
  });
});
