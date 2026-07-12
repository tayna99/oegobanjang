import { useMemo, useState } from 'react';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { SafetyNotice } from '@/components/SafetyNotice';
import { useNextAction } from '@/lib/actionNav';
import { CASE_FILTERS, buildCaseGroups, caseGroupFor, filterCases, type CaseFilterPreset } from '@/lib/cases';
import { CASE_STAGES, DELIVERY_STAGES, caseStageIndex, deliveryStageIndex } from '@/lib/caseStage';
import { severityTone } from '@/lib/chipTone';
import { cn } from '@/lib/cn';
import { dDayLabel, dDayTextClass } from '@/lib/dday';
import { CASE_SHEETS, type CaseSheet } from '@/mocks/fixtures';
import { draftForCase } from '@/mocks/drafts';
import { usableCitations } from '@/stores/citationStore';
import type { CaseCard, Severity } from '@/types';

// PC 케이스 워크벤치(M2.5.4) — reference/design-system/외고반장 PC.dc.html §3b(234~455행)
// "목록 · 상세 · AI/근거 레일" 3열. 데이터는 기존 계약(CaseCard·CASE_SHEETS·DRAFTS)만 사용하고
// 필터·그룹·정렬은 src/lib/cases selector를 그대로 재사용한다(2.1 결정 사항).
// lg 미만에서는 이 컴포넌트가 마운트되지 않는다(useIsDesktop 분기 — 모바일 회귀 차단).

export interface CaseWorkbenchProps {
  cards: CaseCard[];
  preset: CaseFilterPreset;
  selectedCaseId?: string;
  onSelectCase: (caseId: string) => void;
  onSelectFilter: (filter?: string) => void;
  onOpenRun?: (runRef: string) => void; // 3.3 런 체이닝 — 타임라인의 판단 기록 #을 눌러 재생 런으로 진입
}

const SEVERITY_AVATAR: Record<Severity, string> = {
  CRITICAL: 'bg-critbg text-critical',
  HIGH: 'bg-warnbg text-warning',
  MEDIUM: 'bg-medbg text-medium',
  LOW: 'bg-neutbg text-neutral',
};

// 그룹 라벨(승인 대기/즉시 확인 …)을 행 부제·상태 칩에 재사용 — lib/cases의 라벨이 유일한 출처.
function groupLabelFor(card: CaseCard): string {
  const key = caseGroupFor(card);
  const labels: Record<ReturnType<typeof caseGroupFor>, string> = {
    approval_pending: '승인 대기',
    immediate: '즉시 확인',
    review: '확인 필요',
    scheduled: '예정',
    completed: '완료',
  };
  return labels[key];
}

// 아바타 이니셜 — workerRef.displayName의 앞 두 단어 첫 글자("Nguyen V." → NV).
// 근로자 없는 케이스(hiring)는 제목 첫 글자.
function initials(card: CaseCard): string {
  const name = card.workerRef?.displayName;
  if (!name) return card.title.slice(0, 1);
  const parts = name.split(/[\s.]+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
}

function readinessPercent(card: CaseCard, sheet?: CaseSheet): number {
  // 근거 완성도(디자인 §3a 컬럼, 2.5.4b 필드)가 진행바의 1차 소스.
  if (card.evidenceCompleteness !== undefined) return card.evidenceCompleteness;
  if (sheet?.readinessPercent !== undefined) return sheet.readinessPercent;
  return Math.round((caseStageIndex(card, sheet) / (CASE_STAGES.length - 1)) * 100);
}

const RAIL_SECTION_TITLE = 'text-caption1 font-bold tracking-wide text-muted';

function CaseListRow({
  card,
  selected,
  onSelect,
}: {
  card: CaseCard;
  selected: boolean;
  onSelect: () => void;
}) {
  const sheet = CASE_SHEETS[card.caseId];
  const percent = readinessPercent(card, sheet);
  const due = card.dDay !== undefined ? dDayLabel(card.dDay) : '—';
  const dueClass = dDayTextClass(card.dDay);

  return (
    <button
      type="button"
      aria-current={selected}
      aria-label={card.title}
      onClick={onSelect}
      className={cn(
        'flex w-full items-center gap-2.5 border-b border-hairline px-3.5 py-2.5 text-left transition-colors duration-btn ease-v2',
        selected ? 'bg-approvalbg shadow-rail-active' : 'hover:bg-surface',
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'flex size-8 shrink-0 items-center justify-center rounded-full text-caption1 font-bold',
          SEVERITY_AVATAR[card.severity],
        )}
      >
        {initials(card)}
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-pc-sm font-semibold text-ink">{card.title}</span>
        <span className="truncate text-pc-2xs text-subtle">
          {card.workerRef ? `${card.workerRef.team} · ${groupLabelFor(card)}` : groupLabelFor(card)}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1">
        <span className={cn('text-pc-xs font-bold tabular-nums', dueClass)}>{due}</span>
        <span className="h-[3px] w-11 overflow-hidden rounded-full bg-neutbg">
          <span className="block h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
        </span>
      </span>
    </button>
  );
}

// 진행 개요 스테퍼(디자인 §3b 331~345행) — 완료=초록 체크, 현재=파랑+링, 이후=회색.
function StageStepper({ card, sheet }: { card: CaseCard; sheet?: CaseSheet }) {
  const current = caseStageIndex(card, sheet);
  return (
    <div className="flex flex-col gap-2.5">
      <span className={RAIL_SECTION_TITLE}>진행 개요</span>
      <ol className="flex items-start" aria-label="진행 단계">
        {CASE_STAGES.map((stage, index) => {
          const done = index < current || (stage === '실행 (mock)' ? false : index === current && card.state === 'completed');
          const isCurrent = index === current;
          return (
            <li key={stage} className="contents">
              {index > 0 && (
                <span
                  aria-hidden="true"
                  className={cn('mt-2 h-0.5 flex-1', index <= current ? 'bg-success' : 'bg-neutbg')}
                />
              )}
              <span className="flex w-24 flex-col items-center gap-1">
                <span
                  className={cn(
                    'flex size-[18px] items-center justify-center rounded-full',
                    done && !isCurrent && 'bg-success',
                    isCurrent && 'bg-primary shadow-step-current',
                    !done && !isCurrent && 'bg-neutbg shadow-outline-strong',
                  )}
                >
                  {done && !isCurrent && (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M5 12.5L10 17.5L19 7" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </span>
                <span
                  className={cn(
                    'text-center text-caption1 font-semibold',
                    isCurrent ? 'text-primary font-bold' : done ? 'text-ink' : 'text-faint',
                  )}
                >
                  {stage}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function DocChecklist({ sheet }: { sheet: CaseSheet }) {
  if (!sheet.docs || sheet.docs.length === 0) return null;
  const doneCount = sheet.docs.filter((doc) => doc.status === 'received').length;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className={RAIL_SECTION_TITLE}>필수 서류 체크리스트</span>
        <span className="text-pc-2xs text-faint">
          필수 {sheet.docs.length} 중 {doneCount} 완료
        </span>
      </div>
      <ul className="overflow-hidden rounded-in border border-hairline">
        {sheet.docs.map((doc) => (
          <li key={doc.name} className="flex items-center gap-2 border-b border-hairline px-3 py-2 last:border-none">
            {doc.status === 'received' ? (
              <span aria-hidden="true" className="flex size-3.5 items-center justify-center rounded bg-success">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12.5L10 17.5L19 7" stroke="white" strokeWidth="3.5" strokeLinecap="round" />
                </svg>
              </span>
            ) : (
              <span aria-hidden="true" className="size-3.5 rounded shadow-outline-strong" />
            )}
            <span className="flex-1 text-caption1 text-ink">{doc.name}</span>
            <Chip tone={doc.status === 'missing' ? 'critical' : doc.status === 'expiring' ? 'high' : 'neutral'}>
              {doc.statusLabel}
            </Chip>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DraftPanel({ caseId }: { caseId: string }) {
  const draft = draftForCase(caseId);
  if (!draft) return null;
  return (
    <div className="flex flex-col gap-2">
      <span className={RAIL_SECTION_TITLE}>다국어 초안 (AI 생성)</span>
      <div className="flex flex-col gap-2">
        {draft.langs.map((variant) => (
          <div key={variant.lang} className="flex flex-col gap-1">
            <Chip tone={variant.lang === 'ko' ? 'neutral' : 'approval'} className="self-start">
              {variant.label}
            </Chip>
            <p className="whitespace-pre-line rounded-in bg-surface px-3 py-2.5 text-pc-xs leading-relaxed text-muted">
              {variant.text}
            </p>
          </div>
        ))}
      </div>
      <span className="text-pc-2xs text-faint">
        템플릿: {draft.title} · {draft.channel}
      </span>
    </div>
  );
}

function CaseTimeline({ sheet, onOpenRun }: { sheet: CaseSheet; onOpenRun?: (runRef: string) => void }) {
  if (sheet.activity.length === 0 && !sheet.nextWake) return null;
  return (
    <section aria-label="케이스 타임라인" className="flex flex-col gap-2">
      <span className={RAIL_SECTION_TITLE}>케이스 타임라인</span>
      {sheet.activity.length > 0 && (
        <ul className="overflow-hidden rounded-in border border-hairline">
          {sheet.activity.map((entry) => (
            <li key={entry.label} className="flex items-center gap-2.5 border-b border-hairline px-3 py-2 last:border-none">
              <span className="w-20 shrink-0 text-pc-2xs text-faint tabular-nums">{entry.at}</span>
              {/* 3.3 런 체이닝 — runRef가 있으면 재생 런으로 진입하는 버튼, 없으면 정적 텍스트 */}
              {entry.runRef &&
                (onOpenRun ? (
                  <button
                    type="button"
                    onClick={() => onOpenRun(entry.runRef!.replace('#', ''))}
                    className="shrink-0 rounded-badge focus-visible:shadow-rail-focus"
                    aria-label={`판단 기록 ${entry.runRef} 재생 열기`}
                  >
                    <Chip tone="neutral">{entry.runRef}</Chip>
                  </button>
                ) : (
                  <Chip tone="neutral">{entry.runRef}</Chip>
                ))}
              <span className="min-w-0 flex-1 truncate text-caption1 text-ink">
                {entry.label} · {entry.detail}
              </span>
            </li>
          ))}
        </ul>
      )}
      {sheet.nextWake && (
        <p className="rounded-in bg-surface px-3 py-2.5 text-caption1 text-muted">{sheet.nextWake}</p>
      )}
    </section>
  );
}

// 우측 AI/근거 레일(디자인 §3b 396~452행) — AI가 확인한 내용·연결 근거·승인/전달 상태·행정사 전달.
function EvidenceRail({ card, sheet }: { card: CaseCard; sheet: CaseSheet }) {
  const deliveryCurrent = deliveryStageIndex(card);
  return (
    <aside
      aria-label="AI·근거 레일"
      className="flex w-[340px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-hairline bg-canvas p-4"
    >
      {sheet.checkedItems.length > 0 && (
        <section className="flex flex-col gap-2">
          <span className={RAIL_SECTION_TITLE}>AI가 확인한 내용</span>
          <dl className="flex flex-col">
            {sheet.checkedItems.map(({ label, value }) => (
              <div key={label} className="flex justify-between gap-3 border-b border-hairline py-2 text-caption1 last:border-none">
                <dt className="text-muted">{label}</dt>
                <dd className="font-semibold text-ink tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section className="flex flex-col gap-2">
        <span className={RAIL_SECTION_TITLE}>연결 근거 ({sheet.citations.length})</span>
        {sheet.citations.length === 0 ? (
          <p className="rounded-in bg-approvalbg px-3 py-2.5 text-caption1 leading-relaxed text-approval">
            공식 근거가 연결되지 않았습니다. 승인 전 확인이 필요합니다.
          </p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {sheet.citations.map((citation) => (
              <li key={citation.title} className="flex items-center gap-2 rounded-in border border-hairline px-2.5 py-2">
                <span
                  aria-hidden="true"
                  className="flex size-[18px] shrink-0 items-center justify-center rounded bg-approvalbg text-pc-2xs font-bold text-approval"
                >
                  {citation.grade}
                </span>
                <span className="min-w-0 flex-1 truncate text-pc-xs text-ink">{citation.title}</span>
                <span className="shrink-0 text-pc-2xs text-faint">{citation.source}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <span className={RAIL_SECTION_TITLE}>승인 / 전달 상태</span>
        <ol aria-label="전달 단계" className="flex items-start justify-between rounded-in border border-hairline px-3 py-3">
          {DELIVERY_STAGES.map((stage, index) => {
            const done = index < deliveryCurrent;
            const isCurrent = index === deliveryCurrent;
            return (
              <li key={stage} className="contents">
                {index > 0 && (
                  <span
                    aria-hidden="true"
                    className={cn('mx-1 mt-1.5 h-0.5 flex-1', index <= deliveryCurrent ? 'bg-success' : 'bg-neutbg')}
                  />
                )}
                <span className="flex flex-col items-center gap-1">
                  <span
                    aria-hidden="true"
                    className={cn(
                      'size-3.5 rounded-full',
                      done && 'bg-success',
                      isCurrent && 'bg-primary shadow-step-current',
                      !done && !isCurrent && 'bg-neutbg',
                    )}
                  />
                  <span
                    className={cn(
                      'text-pc-2xs font-semibold',
                      isCurrent ? 'font-bold text-primary' : done ? 'text-ink' : 'text-faint',
                    )}
                  >
                    {stage}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      {sheet.nextWake && (
        <section className="flex flex-col gap-2">
          <span className={RAIL_SECTION_TITLE}>다음 액션 (AI 제안)</span>
          <p className="rounded-in border border-hairline px-3 py-2.5 text-pc-xs leading-relaxed text-ink">
            {sheet.nextWake}
          </p>
        </section>
      )}

      <section className="flex flex-col gap-2">
        <span className={RAIL_SECTION_TITLE}>행정사 전달</span>
        <div className="rounded-in border border-hairline p-3">
          <span className="flex h-8 items-center justify-center gap-1.5 rounded-btn-sm text-pc-xs font-semibold text-faint shadow-outline">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="5" y="10" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="2" />
            </svg>
            전달 패키지 준비 (승인 후)
          </span>
        </div>
      </section>

      <p className="mt-auto flex items-center gap-1.5 rounded-in bg-surface px-2.5 py-2 text-pc-2xs text-muted">
        가능/불가능 판단은 제공하지 않습니다.
      </p>
    </aside>
  );
}

export function CaseWorkbench({ cards, preset, selectedCaseId, onSelectCase, onSelectFilter, onOpenRun }: CaseWorkbenchProps) {
  const [query, setQuery] = useState('');
  const handleAction = useNextAction();

  const groups = useMemo(() => buildCaseGroups(cards, preset), [cards, preset]);
  const visibleCards = useMemo(() => {
    const flat = groups.flatMap((group) => group.cases);
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return flat;
    // "이름, 케이스 검색"(§3b placeholder) — 제목 + 근로자명 둘 다 매칭(2.5.4b).
    return flat.filter(
      (card) =>
        card.title.toLowerCase().includes(trimmed) ||
        (card.workerRef?.displayName.toLowerCase().includes(trimmed) ?? false),
    );
  }, [groups, query]);

  // 목록↔상세 동기: URL의 caseId가 진실이고, 없으면 보이는 첫 케이스를 기본 선택한다.
  const selected =
    (selectedCaseId && cards.find((card) => card.caseId === selectedCaseId)) || visibleCards[0];
  const sheet = selected ? CASE_SHEETS[selected.caseId] : undefined;
  // GOTCHAS §2 근거 품질 게이트 — CaseSheet와 동일한 잠금 규칙.
  // F등급(합성 데이터)은 근거로 세지 않는다(§3c 각주 비준, 2.5.4b).
  const citationLocked = sheet ? usableCitations(sheet.citations).length === 0 : true;

  return (
    <section aria-label="케이스 워크벤치" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      {/* 좌: 케이스 목록 레일 (디자인 §3b 263~308행) */}
      <nav aria-label="케이스 목록 레일" className="flex w-[290px] shrink-0 flex-col border-r border-hairline bg-canvas">
        <div className="flex flex-col gap-2 border-b border-hairline px-3.5 pb-2.5 pt-3.5">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="케이스 검색"
            placeholder="이름, 케이스 검색"
            className="h-8 rounded-btn-sm bg-canvas px-2.5 text-caption1 text-ink shadow-outline outline-none placeholder:text-faint focus:shadow-rail-focus"
          />
          <div className="flex flex-wrap gap-1">
            {CASE_FILTERS.map((filter) => {
              const active = filter.key === preset;
              const count = filterCases(cards, filter.key).length;
              return (
                <button
                  key={filter.key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onSelectFilter(filter.key === 'all' ? undefined : filter.key)}
                  className={cn(
                    'rounded-badge px-2 py-0.5 text-caption1 transition-colors duration-btn ease-v2',
                    active
                      ? 'bg-approvalbg font-semibold text-approval shadow-rail-focus'
                      : 'font-medium text-muted shadow-outline hover:bg-surface',
                  )}
                >
                  {filter.label} {count}
                </button>
              );
            })}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {visibleCards.length === 0 ? (
            <p className="px-3.5 py-4 text-caption1 text-muted">조건에 맞는 케이스가 없습니다</p>
          ) : (
            visibleCards.map((card) => (
              <CaseListRow
                key={card.caseId}
                card={card}
                selected={selected?.caseId === card.caseId}
                onSelect={() => onSelectCase(card.caseId)}
              />
            ))
          )}
        </div>
      </nav>

      {/* 중앙: 케이스 상세 (디자인 §3b 310~394행) */}
      <section aria-label="케이스 상세" className="flex min-w-0 flex-1 flex-col bg-canvas">
        {!selected || !sheet ? (
          <p className="p-6 text-body2 text-muted">조건에 맞는 케이스가 없습니다</p>
        ) : (
          <>
            <header className="flex items-start justify-between gap-4 border-b border-hairline px-6 pb-3.5 pt-4">
              <div className="flex min-w-0 items-center gap-3">
                <span
                  aria-hidden="true"
                  className={cn(
                    'flex size-10 shrink-0 items-center justify-center rounded-full text-label1 font-bold',
                    SEVERITY_AVATAR[selected.severity],
                  )}
                >
                  {initials(selected)}
                </span>
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="truncate text-body1 font-bold text-ink">{selected.title}</h2>
                    <Chip tone={severityTone(selected.severity)}>
                      {selected.severity}
                      {selected.dDay !== undefined ? ` · ${dDayLabel(selected.dDay)}` : ''}
                    </Chip>
                    <Chip tone={selected.state === 'human_approved' || selected.state === 'completed' ? 'positive' : 'approval'}>
                      {groupLabelFor(selected)}
                    </Chip>
                  </div>
                  {/* 메타 라인 — §3b 321행 구조("E-9 · 제조1팀 · … · case_002 · 판단 기록 #") */}
                  <p className="truncate text-caption1 text-subtle">
                    {[
                      selected.workerRef && `E-9 · ${selected.workerRef.team} · ${selected.workerRef.nationality}`,
                      selected.stayExpiryDate && `체류만료 ${selected.stayExpiryDate}`,
                      selected.caseCode,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                    {selected.preparedRunRef ? (
                      <>
                        {' · '}
                        {/* 3.3 런 체이닝 — 헤더 판단 기록도 재생 런으로 진입(모바일 2b와 동일 패턴) */}
                        {onOpenRun ? (
                          <button
                            type="button"
                            onClick={() => onOpenRun(selected.preparedRunRef!.replace('#', ''))}
                            className="font-semibold text-primary underline"
                          >
                            판단 기록 {selected.preparedRunRef}
                          </button>
                        ) : (
                          <span className="font-semibold text-primary">판단 기록 {selected.preparedRunRef}</span>
                        )}
                      </>
                    ) : null}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleAction(selected.caseId, selected.secondaryAction)}
                >
                  {selected.secondaryAction.label}
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={citationLocked && selected.primaryAction.requiresApproval}
                  onClick={() => handleAction(selected.caseId, selected.primaryAction)}
                >
                  {selected.primaryAction.label}
                </Button>
              </div>
            </header>

            <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-6 py-4">
              {sheet.guardNote && (
                <p className="rounded-in bg-approvalbg px-3.5 py-3 text-body2 leading-relaxed text-approval">
                  {sheet.guardNote}
                </p>
              )}
              <StageStepper card={selected} sheet={sheet} />
              <div className="grid grid-cols-2 gap-6">
                <DocChecklist sheet={sheet} />
                <DraftPanel caseId={selected.caseId} />
              </div>
              <CaseTimeline sheet={sheet} onOpenRun={onOpenRun} />
            </div>

            <footer className="flex justify-center border-t border-hairline px-6 py-2">
              <SafetyNotice />
            </footer>
          </>
        )}
      </section>

      {selected && sheet && <EvidenceRail card={selected} sheet={sheet} />}
    </section>
  );
}
