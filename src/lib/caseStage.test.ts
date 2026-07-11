import { describe, expect, it } from 'vitest';
import { CASE_STAGES, DELIVERY_STAGES, caseStageIndex, deliveryStageIndex } from './caseStage';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import type { CaseCard, CaseState } from '@/types';

const base = CASE_CARDS[0];
const sheet = CASE_SHEETS[base.caseId];

// agentStage(2.5.4b)는 상태 파생을 덮어쓰므로, 상태 파생 자체를 검증하는 이 파일에서는 제거한다.
function cardWith(state: CaseState): CaseCard {
  return { ...base, state, agentStage: undefined };
}

describe('caseStageIndex — 진행 개요 스테퍼 단계 (디자인 §3b)', () => {
  it.each([
    ['approval_pending', 3],
    ['blocked', 3],
    ['human_approved', 4],
    ['completed', 4],
  ] as [CaseState, number][])('%s → %i (%s)', (state, index) => {
    expect(caseStageIndex(cardWith(state), sheet)).toBe(index);
    expect(CASE_STAGES[index]).toBeDefined();
  });

  it('draft/risk_review는 근거 유무로 갈린다 — 근거 있으면 초안 생성(2), 없으면 근거 수집(1)', () => {
    expect(caseStageIndex(cardWith('draft'), sheet)).toBe(2);
    expect(caseStageIndex(cardWith('risk_review'), undefined)).toBe(1);
  });

  it('agentStage(2.5.4b)가 있으면 상태보다 우선한다 — detected는 상태와 무관하게 0', () => {
    expect(caseStageIndex({ ...cardWith('approval_pending'), agentStage: 'detected' }, sheet)).toBe(0);
    expect(caseStageIndex({ ...cardWith('draft'), agentStage: 'executed' }, sheet)).toBe(4);
  });
});

describe('deliveryStageIndex — 승인/전달 상태 (가드레일: 발송 mock 미도달)', () => {
  it.each([
    ['draft', 0],
    ['risk_review', 0],
    ['approval_pending', 1],
    ['blocked', 1],
    ['human_approved', 2],
  ] as [CaseState, number][])('%s → %i', (state, index) => {
    expect(deliveryStageIndex(cardWith(state))).toBe(index);
  });

  it("completed여도 '발송 (mock)'(3)에는 도달하지 않는다 — 이 MVP는 발송을 실행하지 않는다", () => {
    expect(deliveryStageIndex(cardWith('completed'))).toBe(2);
    expect(deliveryStageIndex(cardWith('completed'))).toBeLessThan(DELIVERY_STAGES.length - 1);
  });
});
