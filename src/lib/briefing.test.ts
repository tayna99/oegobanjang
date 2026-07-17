import { describe, expect, it } from 'vitest';
import { greetingText, recommendReason, visibleCardsForRole } from './briefing';
import type { CaseCard } from '@/types';

function card(overrides: Partial<CaseCard>): CaseCard {
  return {
    caseId: 'x',
    caseCode: 'case_x',
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

// 정렬(severity→dDay→유형→id)은 lib/cases.ts의 sortCaseList 테스트로 통합됐다(D-4,
// NEXT_ROADMAP — 이 파일에 있던 sortCards는 유형 우선순위 타이브레이크가 빠진 중복 구현이었다).
// BriefingHomePage는 이제 sortCaseList를 직접 쓴다.

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

describe('recommendReason', () => {
  it('dDay와 missingDocCount가 모두 있으면 전체 문장을 만든다', () => {
    expect(recommendReason(card({ dDay: 30, missingDocCount: 2 }))).toBe(
      'D-30이고 누락 서류 2건이 있어 오늘 확인이 필요합니다',
    );
  });

  it('dDay만 있으면 짧은 문장을 만든다', () => {
    expect(recommendReason(card({ dDay: -3, missingDocCount: 0 }))).toBe('D+3이라 오늘 확인이 필요합니다');
  });

  it('dDay가 없으면 undefined를 반환한다', () => {
    expect(recommendReason(card({ dDay: undefined }))).toBeUndefined();
  });
});
