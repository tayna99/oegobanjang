import { describe, expect, it } from 'vitest';
import { approvalRefFor, canApproveCase, isCitationLocked, CURRENT_USER } from './approval';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { usableCitations } from '@/stores/citationStore';
import type { CaseCard } from '@/types';

const nguyen = CASE_CARDS.find((c) => c.caseId === 'nguyen')!;
const batbayar = CASE_CARDS.find((c) => c.caseId === 'batbayar')!;
const nguyenUsableCount = usableCitations(CASE_SHEETS.nguyen.citations).length;
const batbayarUsableCount = usableCitations(CASE_SHEETS.batbayar.citations).length;

describe('approvalRefFor — 케이스별 판단 기록 번호(하드코딩 금지, 코드리뷰 F1)', () => {
  it('케이스마다 서로 다른 approval evidenceRef를 준다', () => {
    expect(approvalRefFor('nguyen')).toBe('#4789');
    expect(approvalRefFor('siti')).toBe('#4790');
    // nguyen과 siti가 같은 ref(#4789)를 쓰지 않는다 — 남의 케이스 ref 오기록 방지.
    expect(approvalRefFor('nguyen')).not.toBe(approvalRefFor('siti'));
  });
});

// R2.4 — canApproveCase/isCitationLocked는 CaseSheet 대신 usableCount(number)를 받는다.
// mock은 usableCitations(sheet.citations).length, real은 서버 usable_citation_count를 그대로 넘긴다.
describe('canApproveCase — 상태 전이 합법성 게이트(코드리뷰 A2/B3/F3)', () => {
  it('승인 대기 + 근거 있음이면 승인 가능', () => {
    expect(canApproveCase(nguyen, nguyenUsableCount)).toBe(true);
  });

  it('고위험 blocked 케이스(batbayar)는 근거가 있어도 승인 불가', () => {
    expect(batbayar.state).toBe('blocked');
    expect(isCitationLocked(batbayarUsableCount)).toBe(false); // 근거는 있다
    expect(canApproveCase(batbayar, batbayarUsableCount)).toBe(false); // 그래도 승인 불가
  });

  it('반려(returned)·이미 승인(human_approved)된 케이스는 승인 불가', () => {
    const returned: CaseCard = { ...nguyen, state: 'returned' };
    const approved: CaseCard = { ...nguyen, state: 'human_approved' };
    expect(canApproveCase(returned, nguyenUsableCount)).toBe(false);
    expect(canApproveCase(approved, nguyenUsableCount)).toBe(false);
  });

  it('실사용 근거 0건(citation locked)이면 승인 불가', () => {
    expect(canApproveCase(nguyen, 0)).toBe(false);
    expect(isCitationLocked(0)).toBe(true);
  });
});

describe('CURRENT_USER — evidence actor 단일 출처(코드리뷰 A/F actor 일관성)', () => {
  it('고정 담당자 문자열', () => {
    expect(CURRENT_USER).toBe('김담당');
  });
});
