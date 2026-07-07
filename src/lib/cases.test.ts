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
    expect(groups.map((group) => group.cases.map((item) => item.caseId))).toEqual([
      ['nguyen', 'mohammad'],
      ['bayar'],
      ['tranCase', 'hiring'],
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
      'bayar',
    ]);
    expect(buildCaseGroups(CASE_CARDS, 'approval').flatMap((group) => group.cases.map((item) => item.caseId))).toEqual([
      'nguyen',
      'mohammad',
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

  it('exposes chip labels for supported presets', () => {
    expect(CASE_FILTERS.map((filter) => filter.key)).toEqual(['all', 'crit', 'warn', 'info', 'approval']);
    expect(caseFilterLabel('warn')).toBe('우선 확인');
  });
});