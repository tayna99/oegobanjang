// M1 브리핑 홈 순수 로직 — 1단계 스펙 §M1 "역할 분기(D1)"·"상태 5종 default"·
// 탭별기획 §1.4 마이크로카피. 정렬은 lib/cases.ts의 sortCaseList 하나로 통일했다(D-4,
// NEXT_ROADMAP — 이 파일에 거의 동일한 sortCards가 별도로 있었고 "유형 우선순위" 타이브레이크가
// 빠져 GOTCHAS §4 규칙과 어긋났다). 필터는 여기 한 곳에만(rules/frontend.md
// "파생값은 selector로 — 컴포넌트에서 정렬·필터 로직 재구현 금지").
import type { CaseCard, Role } from '@/types';

const HONORIFIC: Record<Role, string> = {
  manager: '담당자님',
  owner: '대표님',
  viewer: '열람자님',
};

export function greetingText(role: Role, count: number): string {
  if (count === 0) return '오늘 승인할 업무가 없습니다.';
  return `${HONORIFIC[role]}, 오늘 확인이 필요한 업무가 ${count}건 있습니다.`;
}

// 1단계 스펙 §M1 "역할 분기(D1)": owner는 승인 필요 카드만, manager는 전부.
export function visibleCardsForRole(cards: CaseCard[], role: Role): CaseCard[] {
  if (role === 'owner') return cards.filter((c) => c.approvalRequired);
  return cards;
}

// 탭별기획 §1.2 "추천 이유는 항상 '~해서 ~이 필요합니다' 구조" — hero 카드 1장에만 쓴다.
export function recommendReason(card: CaseCard): string | undefined {
  if (card.dDay === undefined) return undefined;
  const dueText = card.dDay >= 0 ? `D-${card.dDay}` : `D+${-card.dDay}`;
  if (card.missingDocCount && card.missingDocCount > 0) {
    return `${dueText}이고 누락 서류 ${card.missingDocCount}건이 있어 오늘 확인이 필요합니다`;
  }
  return `${dueText}이라 오늘 확인이 필요합니다`;
}
