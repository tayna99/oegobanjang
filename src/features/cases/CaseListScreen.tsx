import { useState } from 'react';
import { Chip } from '@/components/Chip';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import {
  CASE_FILTERS,
  caseFilterLabel,
  type CaseFilterPreset,
  type CaseGroup,
  type CaseGroupKey,
} from '@/lib/cases';
import type { CaseCard, Severity } from '@/types';

interface CaseListScreenProps {
  companyName: string;
  totalCount: number;
  preset: CaseFilterPreset;
  groups: CaseGroup[];
  onSelectFilter: (filter?: string) => void;
  onClearFilter: () => void;
  onOpenCase: (caseId: string) => void;
}

const SEVERITY_LABEL: Record<Severity, string> = {
  CRITICAL: '즉시',
  HIGH: '우선',
  MEDIUM: '확인',
  LOW: '참고',
};

const SEVERITY_TONE: Record<Severity, 'critical' | 'high' | 'neutral'> = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'neutral',
  LOW: 'neutral',
};

function dueLabel(card: CaseCard): string | undefined {
  if (card.dDay === undefined) return undefined;
  return card.dDay >= 0 ? `D-${card.dDay}` : `D+${Math.abs(card.dDay)}`;
}

function caseDescription(card: CaseCard): string {
  if (card.missingDocCount && card.missingDocCount > 0) {
    return `서류 ${card.missingDocCount}건 확인이 필요합니다.`;
  }
  if (card.state === 'blocked') return '기한 경과로 담당자 확인이 필요합니다.';
  if (card.state === 'risk_review') return '계약과 체류 일정 확인이 필요합니다.';
  if (card.state === 'draft') return '요청 전 준비 항목을 확인하는 단계입니다.';
  if (card.state === 'human_approved') return '담당자 승인 후 후속 처리를 기다립니다.';
  if (card.state === 'completed') return '처리가 완료된 케이스입니다.';
  return '승인 전 마지막 확인이 필요합니다.';
}

function CaseListItem({ card, onOpenCase }: { card: CaseCard; onOpenCase: (caseId: string) => void }) {
  const due = dueLabel(card);

  return (
    <button
      type="button"
      onClick={() => onOpenCase(card.caseId)}
      className="w-full text-left"
      aria-label={card.title}
    >
      <Card className="space-y-2 p-4 transition hover:border-ink/30 hover:shadow-sm focus-within:border-ink">
        <div className="flex items-start justify-between gap-3">
          <h3 className="min-w-0 flex-1 text-body1 font-semibold leading-snug text-ink">{card.title}</h3>
          <span aria-hidden="true" className="mt-0.5 text-label1 font-semibold text-muted">›</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip tone={SEVERITY_TONE[card.severity]}>{SEVERITY_LABEL[card.severity]}</Chip>
          {due ? <Chip tone={card.dDay !== undefined && card.dDay < 0 ? 'critical' : 'neutral'}>{due}</Chip> : null}
          {/* "승인 필요" 라벨은 그 의미와 일치하는 approval(블루) 톤을 쓴다 — v1은 neutral(회색)로
              텍스트와 색이 어긋나 있었다(2026-07-11 톤 재정비 중 발견, GOTCHAS 임의값 금지 연장선). */}
          {card.approvalRequired ? <Chip tone="approval">승인 필요</Chip> : null}
          {card.missingDocCount ? <Chip tone="high">서류 {card.missingDocCount}</Chip> : null}
        </div>
        {/* 부제 — Mobile §2a 서브라인(근로자 · 팀). 근로자 없는 케이스만 설명 문장 유지. */}
        <p className="truncate text-label1 text-subtle">
          {card.workerRef ? `${card.workerRef.displayName} · ${card.workerRef.team}` : caseDescription(card)}
        </p>
      </Card>
    </button>
  );
}

export function CaseListScreen({
  companyName,
  totalCount,
  preset,
  groups,
  onSelectFilter,
  onClearFilter,
  onOpenCase,
}: CaseListScreenProps) {
  const [expandedGroups, setExpandedGroups] = useState<Partial<Record<CaseGroupKey, boolean>>>({});
  const visibleCount = groups.reduce((sum, group) => sum + group.cases.length, 0);
  const hasAppliedPreset = preset !== 'all';

  function isGroupCollapsed(group: CaseGroup): boolean {
    return group.collapsed && !expandedGroups[group.key];
  }

  function toggleGroup(group: CaseGroup) {
    if (!group.collapsed) return;
    setExpandedGroups((current) => ({ ...current, [group.key]: !current[group.key] }));
  }

  return (
    <main className="mx-auto flex w-full max-w-screen-sm flex-col gap-5 px-4 pb-24 pt-5">
      <header className="space-y-1">
        <h1 className="text-heading2 font-semibold text-ink">케이스</h1>
        <p className="text-label1 text-muted">
          {companyName} · 총 {totalCount}건
        </p>
      </header>

      <section aria-label="케이스 필터" className="space-y-3">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {CASE_FILTERS.map((filter) => {
            const selected = filter.key === preset;
            return (
              <button
                key={filter.key}
                type="button"
                aria-pressed={selected}
                onClick={() => onSelectFilter(filter.key === 'all' ? undefined : filter.key)}
                className={[
                  // rounded-[14px]/border-line은 임의값·미정의 색상 클래스였다(GOTCHAS 위반,
                  // 2026-07-11 토큰 마이그레이션 중 발견해 rounded-chip/border-hairline으로 정정).
                  'h-[38px] shrink-0 rounded-chip border px-4 text-label1 font-semibold transition',
                  selected
                    ? 'border-ink bg-ink text-white'
                    : 'border-hairline bg-surface text-ink hover:border-ink/30',
                ].join(' ')}
              >
                {filter.label}
              </button>
            );
          })}
        </div>

        {hasAppliedPreset ? (
          <div className="flex items-center justify-between rounded-in border border-hairline bg-surface px-3 py-2">
            <span className="text-label1 font-medium text-ink">적용됨: {caseFilterLabel(preset)}</span>
            <Button variant="outline" size="sm" onClick={onClearFilter}>
              해제
            </Button>
          </div>
        ) : null}
      </section>

      {visibleCount === 0 ? (
        <section className="rounded-in border border-hairline bg-surface p-5 text-center">
          <p className="text-body2 text-muted">조건에 맞는 케이스가 없습니다</p>
          {hasAppliedPreset ? (
            <Button className="mt-3" variant="secondary" onClick={onClearFilter}>
              필터 해제
            </Button>
          ) : null}
        </section>
      ) : (
        <section className="space-y-5" aria-label="케이스 그룹">
          {groups
            .filter((group) => group.cases.length > 0 || group.key === 'completed')
            .map((group) => {
              const collapsed = isGroupCollapsed(group);
              const header = (
                <div className="flex h-8 items-center justify-between">
                  <h2 className="text-label1 font-semibold text-muted">
                    {group.label} · {group.cases.length}
                  </h2>
                  {group.collapsed ? (
                    <span className="text-caption1 font-medium text-muted">{collapsed ? '접힘' : '펼침'}</span>
                  ) : null}
                </div>
              );

              return (
                <section key={group.key} className="space-y-3">
                  {group.collapsed ? (
                    <button
                      type="button"
                      className="w-full text-left"
                      aria-expanded={!collapsed}
                      onClick={() => toggleGroup(group)}
                    >
                      {header}
                    </button>
                  ) : (
                    header
                  )}
                  {!collapsed ? (
                    <div className="space-y-3">
                      {group.cases.map((card) => (
                        <CaseListItem key={card.caseId} card={card} onOpenCase={onOpenCase} />
                      ))}
                    </div>
                  ) : null}
                </section>
              );
            })}
        </section>
      )}
    </main>
  );
}