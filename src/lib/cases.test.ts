import { describe, expect, it } from 'vitest';
import { CASE_CARDS } from '@/mocks/fixtures';
import {
  CASE_FILTERS,
  buildCaseGroups,
  caseFilterLabel,
  normalizeCaseFilter,
} from './cases';

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
    expect(groups.map((group) => group.cases.map((card) => card.caseId))).toEqual([
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
    expect(buildCaseGroups(CASE_CARDS, 'crit').flatMap((group) => group.cases.map((card) => card.caseId))).toEqual([
      'bayar',
    ]);
    expect(buildCaseGroups(CASE_CARDS, 'approval').flatMap((group) => group.cases.map((card) => card.caseId))).toEqual([
      'nguyen',
      'mohammad',
    ]);
  });

  it('exposes chip labels for supported presets', () => {
    expect(CASE_FILTERS.map((filter) => filter.key)).toEqual(['all', 'crit', 'warn', 'info', 'approval']);
    expect(caseFilterLabel('warn')).toBe('우선 확인');
  });
});