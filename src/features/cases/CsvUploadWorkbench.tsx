import { useEffect, useState } from 'react';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import type { ChipTone } from '@/lib/chipTone';
import { IconDoc, IconLock } from '@/components/icons';
import { Skeleton } from '@/components/Skeleton';
import { ACTOR_NAME } from '@/lib/approval';
import { cn } from '@/lib/cn';
import { rowsToCards, SAMPLE_CSV_ROWS, validateRows } from '@/lib/csvUpload';
import type { RowStatus, ValidatedCsvRow } from '@/lib/csvUpload';
import { ROLE_LABEL } from '@/lib/role';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

// CSV 일괄 등록(4.4) — reference/design-system/외고반장 CSV 업로드.dc.html §1a 이식.
// PC 워크벤치 크롬(§3b와 동일 실제 Shell, 목업의 52px 나비는 재현하지 않음 — 2026-07-13
// 델타 감사 §3 결정) 위에 4단계(대기→검증 중→결과→완료)를 얹는다. 실제 파일 파싱이
// 없어 "파일 선택" 대신 고정 샘플을 불러오는 각본이다.
type Stage = 'idle' | 'validating' | 'results' | 'done';
type Filter = 'all' | RowStatus;

const VALIDATING_DURATION_MS = 1200;

const STATUS_TONE: Record<RowStatus, ChipTone> = { normal: 'positive', warn: 'high', error: 'critical' };
const STATUS_LABEL: Record<RowStatus, string> = { normal: '정상', warn: '경고', error: '오류' };

const TRACK_STEPS = ['파일 업로드', '형식 검증', '결과 확인', '등록 완료'];
const STAGE_INDEX: Record<Stage, number> = { idle: 0, validating: 1, results: 2, done: 3 };

function ImportStepper({ stage }: { stage: Stage }) {
  const current = STAGE_INDEX[stage];
  return (
    <div className="flex flex-col gap-2.5 p-4">
      <span className="text-caption1 font-bold tracking-wide text-muted">가져오기 단계</span>
      <ol className="flex flex-col">
        {TRACK_STEPS.map((label, index) => {
          const done = index < current;
          const isCurrent = index === current;
          const isLast = index === TRACK_STEPS.length - 1;
          return (
            <li key={label} className="flex gap-3">
              <span className="flex w-5 shrink-0 flex-col items-center">
                <span
                  className={cn(
                    'flex size-5 shrink-0 items-center justify-center rounded-full',
                    done && 'bg-success',
                    isCurrent && 'bg-primary shadow-step-current',
                    !done && !isCurrent && 'bg-neutbg shadow-outline-strong',
                  )}
                >
                  {done && (
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                      <path d="M5 12.5L10 17.5L19 7" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </span>
                {!isLast && <span className={cn('min-h-5 w-0.5 flex-1', done ? 'bg-success' : 'bg-neutbg')} />}
              </span>
              <span className={cn('pb-5 text-pc-sm font-semibold', isCurrent ? 'text-primary' : done ? 'text-ink' : 'text-faint')}>
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function ResultsTable({ rows }: { rows: ValidatedCsvRow[] }) {
  return (
    <div className="flex-1 overflow-y-auto rounded-in border border-hairline">
      <div className="grid grid-cols-[56px_150px_90px_90px_110px_150px_1fr] border-b border-hairline bg-surface">
        {['행', '이름', '국적', '팀', '체류만료일', '외국인등록번호', '상태'].map((h) => (
          <span key={h} className="px-3 py-1.5 text-pc-2xs font-semibold text-muted">{h}</span>
        ))}
      </div>
      {rows.map((row) => (
        <div key={row.rowNo} className="grid grid-cols-[56px_150px_90px_90px_110px_150px_1fr] items-center border-b border-hairline last:border-none">
          <span className="px-3 py-2 text-pc-xs text-faint tabular-nums">{row.rowNo}</span>
          <span className="px-3 py-2 text-pc-sm font-semibold text-ink">{row.name}</span>
          <span className="px-3 py-2 text-pc-xs text-subtle">{row.nationality}</span>
          <span className="px-3 py-2 text-pc-xs text-subtle">{row.team}</span>
          <span className="px-3 py-2 text-pc-xs text-subtle">{row.stayExpiryDateRaw || '—'}</span>
          <span className="px-3 py-2 text-pc-xs tracking-wide text-subtle">{row.externalRegNoMasked}</span>
          <div className="flex flex-col gap-0.5 px-3 py-2">
            <Chip tone={STATUS_TONE[row.status]} className="self-start">{STATUS_LABEL[row.status]}</Chip>
            {row.reason && <span className="text-pc-2xs text-muted">{row.reason}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function CsvUploadWorkbench() {
  const role = useRoleStore((s) => s.role);
  const upsert = useCaseStore((s) => s.upsert);
  const appendEvidence = useEvidenceStore((s) => s.append);

  const [stage, setStage] = useState<Stage>('idle');
  const [filter, setFilter] = useState<Filter>('all');

  useEffect(() => {
    if (stage !== 'validating') return;
    const timer = setTimeout(() => setStage('results'), VALIDATING_DURATION_MS);
    return () => clearTimeout(timer);
  }, [stage]);

  if (role !== 'manager') {
    return (
      <div className="flex h-[calc(100dvh-4rem)] items-center justify-center p-6">
        <p className="text-body2 text-muted">CSV 일괄 등록은 담당자 권한으로만 이용할 수 있습니다.</p>
      </div>
    );
  }

  const rows = validateRows(SAMPLE_CSV_ROWS);
  const visibleRows = filter === 'all' ? rows : rows.filter((r) => r.status === filter);
  const normalRows = rows.filter((r) => r.status === 'normal');
  const counts = {
    all: rows.length,
    normal: normalRows.length,
    warn: rows.filter((r) => r.status === 'warn').length,
    error: rows.filter((r) => r.status === 'error').length,
  };

  const confirmRegister = () => {
    const cards = rowsToCards(rows);
    cards.forEach(upsert);
    appendEvidence({
      id: `csv-import-${Date.now()}`,
      type: 'plan_created',
      at: new Date().toISOString(),
      summary: `CSV 일괄 등록 — 근로자 ${cards.length}명 반영`,
      actor: `${ROLE_LABEL[role]} ${ACTOR_NAME[role]}`,
    });
    setStage('done');
  };

  return (
    <section aria-label="CSV 일괄 등록" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <nav aria-label="가져오기 단계" className="w-[290px] shrink-0 border-r border-hairline bg-canvas">
        <ImportStepper stage={stage} />
      </nav>

      <section className="flex min-w-0 flex-1 flex-col bg-canvas">
        <div className="border-b border-hairline px-6 pb-3 pt-4">
          <p className="text-pc-2xs text-faint">케이스 › CSV로 일괄 등록</p>
          <h1 className="mt-0.5 text-body1 font-bold text-ink">근로자 정보 일괄 등록</h1>
          <p className="text-pc-xs text-subtle">온보딩에서 등록한 첫 근로자와 동일한 형식으로 나머지 인원을 등록합니다</p>
        </div>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-6">
          {stage === 'idle' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 rounded-card border border-dashed border-line bg-surface p-10">
              <span className="flex size-14 items-center justify-center rounded-in bg-approvalbg">
                <IconDoc width={26} height={26} className="text-primary" />
              </span>
              <div className="flex flex-col items-center gap-1 text-center">
                <span className="text-label1 font-semibold text-ink">CSV 파일을 끌어다 놓거나 선택하세요</span>
                <span className="text-caption1 text-muted">필수 컬럼: 이름·국적·팀·체류만료일·외국인등록번호 · UTF-8</span>
              </div>
              <Button variant="primary" onClick={() => setStage('validating')}>
                샘플 CSV 불러오기
              </Button>
            </div>
          )}

          {stage === 'validating' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
              <div className="flex w-full max-w-lg flex-col gap-2.5">
                <div className="mb-1 flex items-center gap-2.5">
                  <span className="size-4 shrink-0 rounded-full bg-primary" />
                  <span className="text-label1 font-semibold text-ink">근로자명단.csv 형식을 확인하는 중</span>
                </div>
                {['96%', '88%', '92%', '80%', '90%'].map((w, i) => (
                  <Skeleton key={i} className="h-3.5" style={{ width: w }} />
                ))}
              </div>
              <span className="text-caption1 text-muted">{SAMPLE_CSV_ROWS.length}행을 확인하고 있어요</span>
            </div>
          )}

          {stage === 'results' && (
            <>
              <div className="flex gap-1.5">
                {(['all', 'normal', 'warn', 'error'] as Filter[]).map((key) => {
                  const active = filter === key;
                  const label = key === 'all' ? '전체' : STATUS_LABEL[key];
                  return (
                    <button
                      key={key}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setFilter(key)}
                      className={cn(
                        'rounded-badge px-2.5 py-1 text-caption1 transition-colors duration-btn ease-v2',
                        active
                          ? 'bg-approvalbg font-semibold text-approval shadow-rail-focus'
                          : 'font-medium text-muted shadow-outline hover:bg-surface',
                      )}
                    >
                      {label} {counts[key]}
                    </button>
                  );
                })}
              </div>
              <ResultsTable rows={visibleRows} />
            </>
          )}

          {stage === 'done' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-succbg">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M6 12.5L10.5 17L18 7.5" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" className="text-success" />
                </svg>
              </span>
              <p className="text-body1 font-bold text-ink">정상 {counts.normal}명이 등록되었습니다</p>
              <p className="text-caption1 leading-relaxed text-muted">
                경고 {counts.warn}건은 보류되었고, 오류 {counts.error}건은 반영되지 않았습니다.
                <br />
                보류·오류 건은 케이스 목록에서 다시 확인할 수 있습니다.
              </p>
              <Button variant="outline" className="mt-1" onClick={() => setStage('idle')}>
                다시 업로드
              </Button>
            </div>
          )}
        </div>

        {stage === 'results' ? (
          <div className="flex items-center justify-between gap-4 border-t border-hairline px-6 py-3">
            <span className="text-pc-2xs text-muted">가능/불가능 판단은 제공하지 않습니다 · 정상 판정된 행만 등록됩니다</span>
            <div className="flex shrink-0 gap-2">
              <Button variant="outline" size="sm" onClick={() => setStage('idle')}>취소</Button>
              <Button variant="primary" size="sm" onClick={confirmRegister}>정상 {counts.normal}명만 등록</Button>
            </div>
          </div>
        ) : (
          stage !== 'done' && (
            <div className="flex items-center justify-center gap-1.5 border-t border-hairline px-6 py-2.5">
              <IconLock width={11} height={11} className="text-subtle" />
              <span className="text-pc-2xs text-muted">가능/불가능 판단은 제공하지 않습니다.</span>
            </div>
          )
        )}
      </section>

      <aside aria-label="CSV 안내" className="flex w-[340px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-hairline bg-canvas p-4">
        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">CSV 형식 안내</span>
          <ul className="overflow-hidden rounded-in border border-hairline">
            {['이름', '국적', '팀', '체류만료일 (YYYY-MM-DD)', '외국인등록번호'].map((col) => (
              <li key={col} className="flex items-center gap-2 border-b border-hairline px-3 py-2 last:border-none">
                <span className="flex size-3.5 shrink-0 items-center justify-center rounded bg-success">
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none">
                    <path d="M5 12.5L10 17.5L19 7" stroke="white" strokeWidth="3.5" strokeLinecap="round" />
                  </svg>
                </span>
                <span className="text-pc-xs text-ink">{col}</span>
              </li>
            ))}
          </ul>
          <Button variant="outline" size="sm">템플릿 다운로드</Button>
        </section>

        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">마스킹 안내</span>
          <div className="flex gap-2 rounded-in bg-surface p-3">
            <IconLock width={14} height={14} className="mt-0.5 shrink-0 text-subtle" />
            <span className="text-pc-xs leading-relaxed text-muted">
              외국인등록번호는 업로드 즉시 마스킹되어 저장됩니다. 원문 전체 번호는 저장하지 않습니다.
            </span>
          </div>
        </section>

        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">상태 기준</span>
          <div className="flex flex-col gap-1.5">
            {(['normal', 'warn', 'error'] as RowStatus[]).map((status) => (
              <div key={status} className="flex gap-2">
                <Chip tone={STATUS_TONE[status]} className="mt-0.5 shrink-0">{STATUS_LABEL[status]}</Chip>
                <span className="text-pc-xs leading-relaxed text-ink">
                  {status === 'normal' && '필수 값과 형식을 모두 확인했습니다'}
                  {status === 'warn' && '값은 있으나 형식 확인이 필요합니다'}
                  {status === 'error' && '필수 값이 없거나 형식이 맞지 않습니다'}
                </span>
              </div>
            ))}
          </div>
        </section>
      </aside>
    </section>
  );
}
