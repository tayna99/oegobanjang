import type { CaseCard, Severity } from '@/types';

export type CaseFilterPreset = 'all' | 'crit' | 'warn' | 'info' | 'approval';

export type CaseGroupKey =
  | 'approval_pending'
  | 'immediate'
  | 'review'
  | 'scheduled'
  | 'completed';

export interface CaseFilterOption {
  key: CaseFilterPreset;
  label: string;
}

export interface CaseGroup {
  key: CaseGroupKey;
  label: string;
  collapsed: boolean;
  cases: CaseCard[];
}

export const CASE_FILTERS: CaseFilterOption[] = [
  { key: 'all', label: '전체' },
  { key: 'crit', label: '즉시 확인' },
  { key: 'warn', label: '우선 확인' },
  { key: 'info', label: '확인 필요' },
  { key: 'approval', label: '승인 대기' },
];

const FILTER_KEYS = new Set<CaseFilterPreset>(CASE_FILTERS.map((filter) => filter.key));

const GROUPS: Array<Omit<CaseGroup, 'cases'>> = [
  { key: 'approval_pending', label: '승인 대기', collapsed: false },
  { key: 'immediate', label: '즉시 확인', collapsed: false },
  { key: 'review', label: '확인 필요', collapsed: false },
  { key: 'scheduled', label: '예정', collapsed: false },
  { key: 'completed', label: '완료', collapsed: true },
];

const SEVERITY_RANK: Record<Severity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

export function normalizeCaseFilter(value: string | null | undefined): CaseFilterPreset {
  return value && FILTER_KEYS.has(value as CaseFilterPreset) ? (value as CaseFilterPreset) : 'all';
}

export function caseFilterLabel(preset: CaseFilterPreset): string {
  return CASE_FILTERS.find((filter) => filter.key === preset)?.label ?? '전체';
}

export function caseGroupFor(card: CaseCard): CaseGroupKey {
  if (card.state === 'approval_pending') return 'approval_pending';
  if (card.state === 'completed' || card.state === 'human_approved') return 'completed';
  if (card.state === 'blocked' || card.severity === 'CRITICAL' || (card.dDay ?? 1) < 0) return 'immediate';
  if (card.state === 'risk_review' || card.state === 'draft') return 'review';
  return 'scheduled';
}

export function sortCaseList(cards: CaseCard[]): CaseCard[] {
  return [...cards].sort((a, b) => {
    const bySeverity = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    if (bySeverity !== 0) return bySeverity;
    const aDay = a.dDay ?? Number.POSITIVE_INFINITY;
    const bDay = b.dDay ?? Number.POSITIVE_INFINITY;
    if (aDay !== bDay) return aDay - bDay;
    return a.caseId.localeCompare(b.caseId);
  });
}

function matchesFilter(card: CaseCard, preset: CaseFilterPreset): boolean {
  if (preset === 'all') return true;
  if (preset === 'approval') return card.state === 'approval_pending';
  if (preset === 'crit') return card.severity === 'CRITICAL' || card.state === 'blocked' || (card.dDay ?? 1) < 0;
  if (preset === 'warn') return card.severity === 'HIGH';
  return card.severity === 'MEDIUM' || card.state === 'risk_review' || card.state === 'draft';
}

export function filterCases(cards: CaseCard[], preset: CaseFilterPreset): CaseCard[] {
  return cards.filter((card) => matchesFilter(card, preset));
}

export function buildCaseGroups(cards: CaseCard[], preset: CaseFilterPreset): CaseGroup[] {
  const grouped = new Map<CaseGroupKey, CaseCard[]>();
  for (const card of filterCases(cards, preset)) {
    const key = caseGroupFor(card);
    grouped.set(key, [...(grouped.get(key) ?? []), card]);
  }

  return GROUPS.map((group) => ({
    ...group,
    cases: sortCaseList(grouped.get(group.key) ?? []),
  }));
}