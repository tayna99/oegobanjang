import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BottomSheet } from '@/components/BottomSheet';
import { Chip } from '@/components/Chip';
import { cn } from '@/lib/cn';
import { AUDIT_FILTERS, AUDIT_TYPE_LABEL, AUDIT_TYPE_TONE, filterAudit, mergedAuditLog, type AuditFilterKey } from '@/lib/audit';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { EvidenceEvent } from '@/types';

// M8 전역 판단 기록(모바일) — 블루프린트 §9-A: 2d 타임라인 + §3c 감사 행을 전역 스코프로 재사용(2.3).
// 감사 가능한 판단 이력 최신순 + 필터 + 상세 시트. 해시만 표시(원문 없음). 딥링크 ?ref= 하이라이트.
// reference/specs/1단계_화면상태스펙_M1-M9_v1.md §M8, 탭별기획 §4.2(사람 결정만 primary).

function time(iso: string): string {
  // "2026-07-09T16:02:00Z" → "07/09 16:02" (데모 고정값 표기).
  return `${iso.slice(5, 7)}/${iso.slice(8, 10)} ${iso.slice(11, 16)}`;
}

export function GlobalEvidencePage() {
  const events = useEvidenceStore((s) => s.events);
  const [searchParams] = useSearchParams();
  const highlightRef = searchParams.get('ref');
  const [filter, setFilter] = useState<AuditFilterKey>('all');
  const [selected, setSelected] = useState<EvidenceEvent | null>(null);

  const entries = useMemo(() => filterAudit(mergedAuditLog(events), filter), [events, filter]);

  return (
    <div className="mx-auto flex w-full max-w-screen-sm flex-col gap-4 px-4 pb-24 pt-5">
      <header className="flex flex-col gap-0.5">
        <h1 className="text-heading2 font-bold text-ink">판단 기록</h1>
        <p className="text-pc-sm text-subtle">감사 가능한 판단 이력 · 최신순</p>
      </header>

      <div className="flex flex-wrap gap-1.5" role="group" aria-label="판단 기록 필터">
        {AUDIT_FILTERS.map((option) => {
          const active = option.key === filter;
          return (
            <button
              key={option.key}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(option.key)}
              className={cn(
                'rounded-badge px-2.5 py-1 text-caption1 transition-colors duration-btn ease-v2',
                active
                  ? 'bg-approvalbg font-semibold text-approval shadow-rail-focus'
                  : 'font-medium text-muted shadow-outline hover:bg-surface',
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {entries.length === 0 ? (
        <p className="rounded-in bg-surface px-3.5 py-3 text-body2 text-muted">해당 유형의 기록이 없습니다.</p>
      ) : (
        <ol className="flex flex-col gap-2">
          {entries.map((entry) => {
            const highlighted = highlightRef !== null && entry.evidenceRef === highlightRef;
            const human = entry.type === 'approval_decided';
            return (
              <li key={entry.id}>
                <button
                  type="button"
                  aria-label={`${AUDIT_TYPE_LABEL[entry.type]} · ${entry.summary ?? ''}`}
                  onClick={() => setSelected(entry)}
                  className={cn(
                    'flex w-full flex-col gap-1 rounded-in border px-3.5 py-3 text-left transition-shadow duration-btn ease-v2',
                    highlighted ? 'border-primary shadow-rail-focus' : 'border-hairline',
                  )}
                >
                  <div className="flex items-center gap-2">
                    {entry.evidenceRef && (
                      <span className={cn('text-caption1 font-bold', human ? 'text-primary' : 'text-ink')}>
                        {entry.evidenceRef}
                      </span>
                    )}
                    <Chip tone={AUDIT_TYPE_TONE[entry.type]}>{AUDIT_TYPE_LABEL[entry.type]}</Chip>
                    <span className="ml-auto text-pc-2xs text-dim tabular-nums">{time(entry.at)}</span>
                  </div>
                  <span className="text-label1 text-ink">{entry.summary}</span>
                  <span className="text-caption1 text-subtle">{entry.actor ?? 'system'}</span>
                </button>
              </li>
            );
          })}
        </ol>
      )}

      <BottomSheet open={selected !== null} onClose={() => setSelected(null)}>
        {selected && (
          <div className="flex flex-col gap-3 pb-2">
            <div className="flex items-center gap-2">
              <Chip tone={AUDIT_TYPE_TONE[selected.type]}>{AUDIT_TYPE_LABEL[selected.type]}</Chip>
              {selected.evidenceRef && <span className="text-label1 font-bold text-primary">{selected.evidenceRef}</span>}
            </div>
            <h3 className="text-body1 font-semibold text-ink">{selected.summary}</h3>
            <dl className="flex flex-col gap-2">
              {[
                ['시각', time(selected.at)],
                ['행위자', selected.actor ?? 'system'],
                ['케이스', selected.caseId ?? '—'],
                ['해시', selected.hash ?? '해시 없음(요약 이벤트)'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-3 border-b border-hairline py-2 text-label1 last:border-none">
                  <dt className="text-muted">{label}</dt>
                  <dd className={cn('text-right text-ink', label === '해시' && 'font-mono text-caption1')}>{value}</dd>
                </div>
              ))}
            </dl>
            <p className="rounded-in bg-surface px-3.5 py-3 text-caption1 leading-relaxed text-subtle">
              판단 기록은 INSERT-only로 저장되며 원문·개인정보는 해시로만 남습니다. 정정도 새 이벤트로 추가됩니다.
            </p>
          </div>
        )}
      </BottomSheet>
    </div>
  );
}
