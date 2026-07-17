import { describe, expect, it } from 'vitest';
import { CASE_CARDS } from '@/mocks/fixtures';
import type { CaseCard } from '@/types';
import {
  CASE_FILTERS,
  buildCaseGroups,
  caseFilterLabel,
  normalizeCaseFilter,
  sortCaseList,
} from './cases';

function card(overrides: Partial<CaseCard>): CaseCard {
  return {
    ...CASE_CARDS[0],
    caseId: overrides.caseId ?? 'case',
    title: overrides.title ?? overrides.caseId ?? 'case',
    severity: overrides.severity ?? 'MEDIUM',
    dDay: overrides.dDay ?? 10,
    state: overrides.state ?? 'risk_review',
    primaryAction: {
      ...CASE_CARDS[0].primaryAction,
      actionId: `${overrides.caseId ?? 'case'}-action`,
      kind: overrides.primaryAction?.kind ?? 'detail',
    },
    secondaryAction: {
      ...CASE_CARDS[0].secondaryAction,
      actionId: `${overrides.caseId ?? 'case'}-secondary`,
    },
    ...overrides,
  };
}

describe('case list selectors', () => {
  it('groups cases in the fixed M7 order and sorts each group deterministically', () => {
    const groups = buildCaseGroups(CASE_CARDS, 'all');

    expect(groups.map((group) => group.key)).toEqual([
      'approval_pending',
      'immediate',
      'review',
      'scheduled',
      'completed',
    ]);
    // 6인 로스터(2.5.4b): 승인 대기 = siti(D-3)·nguyen(D-30) — 같은 HIGH라 D-day 오름차순.
    expect(groups.map((group) => group.cases.map((item) => item.caseId))).toEqual([
      ['siti', 'nguyen'],
      ['batbayar'],
      ['tranCase', 'rahmat', 'oyunaa'],
      [],
      [],
    ]);
  });

  it('normalizes unknown deep-link filters to all', () => {
    expect(normalizeCaseFilter('crit')).toBe('crit');
    expect(normalizeCaseFilter('approval')).toBe('approval');
    expect(normalizeCaseFilter('missing')).toBe('all');
    expect(normalizeCaseFilter(null)).toBe('all');
  });

  it('applies deep-link presets before grouping', () => {
    expect(buildCaseGroups(CASE_CARDS, 'crit').flatMap((group) => group.cases.map((item) => item.caseId))).toEqual([
      'batbayar',
    ]);
    expect(buildCaseGroups(CASE_CARDS, 'approval').flatMap((group) => group.cases.map((item) => item.caseId))).toEqual([
      'siti',
      'nguyen',
    ]);
  });

  it('uses severity, d-day, action type, then id as deterministic sort keys', () => {
    const sorted = sortCaseList([
      card({ caseId: 'z-detail', primaryAction: { ...CASE_CARDS[0].primaryAction, kind: 'detail' } }),
      card({ caseId: 'b-draft', primaryAction: { ...CASE_CARDS[0].primaryAction, kind: 'draft' } }),
      card({ caseId: 'a-approve', primaryAction: { ...CASE_CARDS[0].primaryAction, kind: 'approve' } }),
    ]);

    expect(sorted.map((item) => item.caseId)).toEqual(['a-approve', 'b-draft', 'z-detail']);
  });

  // D-4(NEXT_ROADMAP): briefing.ts의 중복 sortCards에 있던 개별 엣지케이스를 이관.
  it('severity 순서(CRITICAL > HIGH > MEDIUM > LOW)로 정렬한다', () => {
    const sorted = sortCaseList([
      card({ caseId: 'low', severity: 'LOW' }),
      card({ caseId: 'crit', severity: 'CRITICAL' }),
      card({ caseId: 'high', severity: 'HIGH' }),
    ]);
    expect(sorted.map((c) => c.caseId)).toEqual(['crit', 'high', 'low']);
  });

  it('severity가 같으면 dDay 오름차순(더 급한 것 먼저)으로 정렬한다', () => {
    const sorted = sortCaseList([
      card({ caseId: 'a', severity: 'HIGH', dDay: 30 }),
      card({ caseId: 'b', severity: 'HIGH', dDay: -3 }),
      card({ caseId: 'c', severity: 'HIGH', dDay: 5 }),
    ]);
    expect(sorted.map((c) => c.caseId)).toEqual(['b', 'c', 'a']);
  });

  it('dDay가 없는 카드는 있는 카드보다 뒤로 간다', () => {
    const sorted = sortCaseList([card({ caseId: 'nodday', dDay: undefined }), card({ caseId: 'hasday', dDay: 10 })]);
    expect(sorted.map((c) => c.caseId)).toEqual(['hasday', 'nodday']);
  });

  it('exposes chip labels for supported presets', () => {
    expect(CASE_FILTERS.map((filter) => filter.key)).toEqual(['all', 'crit', 'warn', 'info', 'approval']);
    expect(caseFilterLabel('warn')).toBe('우선 확인');
  });
});