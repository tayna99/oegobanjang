import { useMemo, useState } from 'react';
import { Chip } from '@/components/Chip';
import { KpiTile } from '@/components/KpiTile';
import type { ChipTone } from '@/lib/chipTone';
import { cn } from '@/lib/cn';
import { AUDIT_FILTERS, AUDIT_TYPE_LABEL, AUDIT_TYPE_TONE, filterAudit, mergedAuditLog, type AuditFilterKey } from '@/lib/audit';
import { SECTION_TITLE_CLASS } from '@/lib/sectionTitle';
import { CASE_SHEETS } from '@/mocks/fixtures';
import { citationKpis, linkedCaseCount, useCitationStore } from '@/stores/citationStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { CitationGrade, CitationStatus } from '@/types';

// PC 거버넌스(§3c) — reference/design-system/외고반장 PC.dc.html §3c(457~608행) 이식(2.5.5).
// 좌: 근거 라이브러리(등급·최신성·연계 케이스 · KPI 파생) / 우: 감사 로그(필터·해시 · INSERT-only).
// 데스크톱 전용(EvidencePage가 useIsDesktop으로 분기) — Shell lg 헤더(h-16) 아래를 채운다.
// 근거 등록/정책 룰 엔진은 post-MVP(§3c 헤더 문구) — 라이브러리는 읽기 전용.

const GRADE_TONE: Record<CitationGrade, ChipTone> = {
  A: 'approval',
  B: 'approval',
  C: 'neutral',
  E: 'neutral',
  F: 'critical', // 합성 데이터 — 근거 사용 불가
};

const STATUS_TONE: Record<CitationStatus, ChipTone> = {
  official: 'positive',
  review_needed: 'high',
  stale: 'critical',
  internal: 'neutral',
};

const STATUS_LABEL: Record<CitationStatus, string> = {
  official: '공식 근거',
  review_needed: '검토 필요',
  stale: '부족 (stale)',
  internal: '내부 기준',
};

const SECTION_TITLE = SECTION_TITLE_CLASS;

function CitationLibrary() {
  const records = useCitationStore((s) => s.records);
  const kpis = useMemo(() => citationKpis(records), [records]);
  const sheets = useMemo(() => Object.values(CASE_SHEETS), []);

  return (
    <section aria-label="근거 라이브러리" className="flex min-w-0 flex-1 flex-col gap-4 overflow-y-auto p-6">
      <header className="flex flex-col gap-1">
        <h2 className="text-heading2 font-bold text-ink">근거 라이브러리</h2>
        <p className="text-caption1 text-subtle">모든 판단·초안의 근거가 되는 자료 · RAG 인덱스 연동</p>
      </header>

      <div className="grid grid-cols-5 gap-2">
        <KpiTile label="전체" value={kpis.total} tone="text-ink" />
        <KpiTile label="공식 근거 (A·B)" value={kpis.official} tone="text-approval" />
        <KpiTile label="최신성 확인" value={kpis.fresh} tone="text-success" />
        <KpiTile label="검토 필요" value={kpis.reviewNeeded} tone="text-warning" />
        <KpiTile label="부족 (stale)" value={kpis.stale} tone="text-critical" />
      </div>

      <div className="overflow-hidden rounded-in border border-hairline">
        <div className="grid grid-cols-[52px_1fr_150px_110px_110px_84px] items-center gap-2 border-b border-hairline bg-surface px-3 py-2 text-pc-2xs font-bold text-subtle">
          <span>등급</span>
          <span>근거 제목</span>
          <span>출처 / 기관</span>
          <span>최신성 확인</span>
          <span>상태</span>
          <span className="text-right">연계</span>
        </div>
        <ul>
          {records.map((record) => (
            <li
              key={record.id}
              className="grid grid-cols-[52px_1fr_150px_110px_110px_84px] items-center gap-2 border-b border-hairline px-3 py-2.5 last:border-none"
            >
              <span>
                <Chip tone={GRADE_TONE[record.grade]}>{record.grade}</Chip>
              </span>
              <span className="min-w-0 truncate text-label1 text-ink">{record.title}</span>
              <span className="truncate text-caption1 text-subtle">{record.source}</span>
              <span
                className={cn(
                  'text-caption1 tabular-nums',
                  record.status === 'stale' ? 'text-critical' : record.status === 'review_needed' ? 'text-warning' : 'text-dim',
                )}
              >
                {record.updatedAt}
              </span>
              <span>
                <Chip tone={STATUS_TONE[record.status]}>{STATUS_LABEL[record.status]}</Chip>
              </span>
              <span className="text-right text-caption1 font-semibold tabular-nums text-ink">
                {linkedCaseCount(record.id, sheets)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="text-caption1 leading-relaxed text-subtle">
        근거 없는 케이스는 승인이 잠깁니다. F등급(합성 데이터)은 근거로 사용할 수 없습니다.
      </p>
    </section>
  );
}

function AuditLog() {
  const events = useEvidenceStore((s) => s.events);
  const [filter, setFilter] = useState<AuditFilterKey>('all');
  const entries = useMemo(() => filterAudit(mergedAuditLog(events), filter), [events, filter]);

  return (
    <aside aria-label="감사 로그" className="flex w-[470px] shrink-0 flex-col gap-3 overflow-y-auto border-l border-hairline bg-canvas p-5">
      <h2 className={SECTION_TITLE}>감사 로그 (Audit Log)</h2>

      <div className="flex flex-wrap gap-1.5">
        {AUDIT_FILTERS.map((option) => {
          const active = option.key === filter;
          return (
            <button
              key={option.key}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(option.key)}
              className={cn(
                'rounded-badge px-2 py-0.5 text-caption1 transition-colors duration-btn ease-v2',
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
        <p className="rounded-in bg-surface px-3 py-2.5 text-caption1 text-muted">해당 유형의 기록이 없습니다.</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {entries.map((entry) => (
            <li key={entry.id} className="flex flex-col gap-1 rounded-in border border-hairline px-3 py-2.5">
              <div className="flex items-center gap-2">
                {entry.evidenceRef && <span className="text-caption1 font-bold text-primary">{entry.evidenceRef}</span>}
                <Chip tone={AUDIT_TYPE_TONE[entry.type]}>{AUDIT_TYPE_LABEL[entry.type]}</Chip>
                <span className="ml-auto text-pc-2xs text-dim tabular-nums">{entry.actor ?? 'system'}</span>
              </div>
              <span className="text-caption1 text-ink">{entry.summary}</span>
              {entry.hash && <span className="font-mono text-pc-2xs text-dim">{entry.hash}</span>}
            </li>
          ))}
        </ul>
      )}

      <p className="mt-auto pt-1 text-pc-2xs text-subtle">INSERT-only · 원문 PII 미저장 (해시만 기록)</p>
    </aside>
  );
}

export function GovernancePage() {
  return (
    <section aria-label="거버넌스" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <CitationLibrary />
      <AuditLog />
    </section>
  );
}
