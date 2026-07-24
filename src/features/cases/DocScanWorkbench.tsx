// 서류 스캔 분류(R5.2) — reference/design-system/외고반장 서류 스캔 분류.dc.html §1a 이식.
// docs/DESIGN_SYNC_AUDIT_2026-07-17.md §2 — 우측 레일 내부 플로우가 아니라 CsvUploadWorkbench와
// 같은 자체 워크벤치(좌 스텝트래커 290px·중앙 플로우·우 안내 레일 340px)다. OCR 파이프라인이
// 없어 lib/docScan.ts의 파일명 키워드 결정론적 분류만 쓴다.
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { IconDoc, IconLock } from '@/components/icons';
import { Skeleton } from '@/components/Skeleton';
import { ACTOR_NAME } from '@/lib/approval';
import { cn } from '@/lib/cn';
import { useSeedCases } from '@/lib/dataSeed';
import { classifyScanFiles, hasUnresolvedRows, SCAN_DOC_TYPES } from '@/lib/docScan';
import type { ScanMatchStatus, ScanResult } from '@/lib/docScan';
import type { ChipTone } from '@/lib/chipTone';
import { ROLE_LABEL } from '@/lib/role';
import { CASE_SHEETS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

type Stage = 'idle' | 'classifying' | 'review' | 'done';
type Filter = 'all' | ScanMatchStatus;

const CLASSIFYING_DURATION_MS = 1200;

const STATUS_TONE: Record<ScanMatchStatus, ChipTone> = { matched: 'positive', low_confidence: 'high', unmatched: 'critical' };
const STATUS_LABEL: Record<ScanMatchStatus, string> = { matched: '정상 매칭', low_confidence: '확인 필요', unmatched: '미매칭' };

const TRACK_STEPS = ['업로드', '분류 중', '결과 확인', '확인 대기 반영'];
const STAGE_INDEX: Record<Stage, number> = { idle: 0, classifying: 1, review: 2, done: 3 };

function ScanStepper({ stage }: { stage: Stage }) {
  const current = STAGE_INDEX[stage];
  return (
    <div className="flex flex-col gap-2.5 p-4">
      <span className="text-caption1 font-bold tracking-wide text-muted">분류 단계</span>
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

// 썸네일은 항상 장식용 placeholder다 — 실제 업로드 파일을 렌더링하지 않는다(감사 §2.1,
// PII 원문 노출 구조적 차단이 마스킹 처리보다 더 안전한 선택).
function ScanThumbnail() {
  return (
    <div className="flex h-11 w-16 shrink-0 flex-col justify-center gap-0.5 rounded bg-canvas p-1.5 shadow-outline">
      <span className="h-1 w-3/4 rounded-full bg-line" />
      <span className="h-1 w-1/2 rounded-full bg-line" />
      <span className="flex h-1.5 w-4/5 items-center justify-center rounded-full bg-ink">
        <IconLock width={6} height={6} className="text-canvas" />
      </span>
      <span className="h-1 w-2/5 rounded-full bg-line" />
    </div>
  );
}

function CorrectionPanel({
  result,
  workerOptions,
  onPickWorker,
  onPickDocType,
  onClose,
}: {
  result: ScanResult;
  workerOptions: string[];
  onPickWorker: (name: string) => void;
  onPickDocType: (docType: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="col-span-full flex flex-col gap-3 border-t border-hairline bg-surface px-5 py-3.5">
      <div className="flex flex-col gap-1.5">
        <span className="text-pc-2xs font-semibold text-muted">근로자 지정</span>
        <div className="flex flex-wrap gap-1.5">
          {workerOptions.map((name) => (
            <button
              key={name}
              type="button"
              aria-pressed={result.workerName === name}
              onClick={() => onPickWorker(name)}
              className={cn(
                'rounded-badge px-3 py-1.5 text-caption1 font-semibold transition-colors duration-btn ease-v2',
                result.workerName === name ? 'bg-approvalbg text-approval shadow-rail-focus' : 'text-muted shadow-outline hover:bg-canvas',
              )}
            >
              {name}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <span className="text-pc-2xs font-semibold text-muted">서류 유형 지정</span>
        <div className="flex flex-wrap gap-1.5">
          {SCAN_DOC_TYPES.map((docType) => (
            <button
              key={docType}
              type="button"
              aria-pressed={result.docType === docType}
              onClick={() => onPickDocType(docType)}
              className={cn(
                'rounded-badge px-3 py-1.5 text-caption1 font-semibold transition-colors duration-btn ease-v2',
                result.docType === docType ? 'bg-approvalbg text-approval shadow-rail-focus' : 'text-muted shadow-outline hover:bg-canvas',
              )}
            >
              {docType}
            </button>
          ))}
        </div>
      </div>
      <Button variant="secondary" size="sm" className="self-end" onClick={onClose}>
        적용
      </Button>
    </div>
  );
}

export function DocScanWorkbench({ onCancel }: { onCancel: () => void }) {
  const role = useRoleStore((s) => s.role);
  const cases = useCaseStore((s) => s.cases);
  const applyInterpretationUpdates = useCaseStore((s) => s.applyInterpretationUpdates);
  const appendEvidence = useEvidenceStore((s) => s.append);

  const [stage, setStage] = useState<Stage>('idle');
  const [filter, setFilter] = useState<Filter>('all');
  const [results, setResults] = useState<ScanResult[]>([]);
  const [openRowId, setOpenRowId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useSeedCases();

  const workers = Object.values(cases).filter((card) => card.workerRef);

  useEffect(() => {
    if (stage !== 'classifying') return;
    const timer = setTimeout(() => setStage('review'), CLASSIFYING_DURATION_MS);
    return () => clearTimeout(timer);
  }, [stage]);

  const onFiles = (fileList: FileList) => {
    const fileNames = [...fileList].map((f) => f.name);
    setResults(classifyScanFiles(fileNames, workers));
    setStage('classifying');
  };

  if (role !== 'manager') {
    return (
      <div className="flex h-[calc(100dvh-4rem)] items-center justify-center p-6">
        <p className="text-body2 text-muted">서류 스캔 분류는 담당자 권한으로만 이용할 수 있습니다.</p>
      </div>
    );
  }

  const visibleResults = filter === 'all' ? results : results.filter((r) => r.status === filter);
  const counts = {
    all: results.length,
    matched: results.filter((r) => r.status === 'matched').length,
    low_confidence: results.filter((r) => r.status === 'low_confidence').length,
    unmatched: results.filter((r) => r.status === 'unmatched').length,
  };
  const blocked = hasUnresolvedRows(results);

  const updateResult = (fileId: string, patch: Partial<ScanResult>) => {
    setResults((prev) =>
      prev.map((r) => {
        if (r.fileId !== fileId) return r;
        const next = { ...r, ...patch };
        const hasWorker = !!next.workerName;
        const hasDoc = !!next.docType;
        // 근로자가 아직 없으면 서류 유형만 지정해도 unmatched에서 벗어나지 않는다(ui-matcher
        // 지적 — hasUnresolvedRows는 status==='unmatched'만 보므로, 여기서 low_confidence로
        // 잘못 승격시키면 근로자 미상 행이 게이트를 통과해버린다. hasWorker가 참이 되기
        // 전까지는 원래 status를 유지한다).
        next.status = hasWorker && hasDoc ? 'matched' : hasWorker ? 'low_confidence' : r.status;
        return next;
      }),
    );
  };

  const confirmPending = () => {
    if (blocked) return;
    // 완료 문구·evidence 건수는 항상 results.length(스캔된 전체 파일 수) 기준이다(감사 §2.3 —
    // 목업 완료 메시지도 일부 제외 언급 없이 전체 건수를 말한다). 서류 유형이 끝내 지정되지
    // 않은 행은 반영할 doc.name 필드 자체가 없어 caseStore 갱신에서만 조용히 제외된다.
    for (const result of results) {
      if (!result.caseId || !result.docType) continue;
      const sheet = CASE_SHEETS[result.caseId];
      const from = sheet?.docs?.find((d) => d.name === result.docType)?.statusLabel ?? '누락';
      applyInterpretationUpdates(result.caseId, [
        { updateId: `scan-${result.fileId}`, field: result.docType, from, to: '스캔 확인 대기', badgeTone: 'warning' },
      ]);
    }
    appendEvidence({
      id: `doc-scan-${Date.now()}`,
      type: 'tool_executed',
      at: new Date().toISOString(),
      summary: `서류 스캔 분류 — ${results.length}건 확인 대기 반영`,
      actor: `${ROLE_LABEL[role]} ${ACTOR_NAME[role]}`,
    });
    setStage('done');
  };

  const reset = () => {
    setStage('idle');
    setResults([]);
    setFilter('all');
    setOpenRowId(null);
  };

  return (
    <section aria-label="서류 스캔 분류" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <nav aria-label="분류 단계" className="w-[290px] shrink-0 border-r border-hairline bg-canvas">
        <ScanStepper stage={stage} />
      </nav>

      <section className="flex min-w-0 flex-1 flex-col bg-canvas">
        <div className="border-b border-hairline px-6 pb-3 pt-4">
          <p className="text-pc-2xs text-faint">케이스 › 서류 스캔 분류</p>
          <h1 className="mt-0.5 text-body1 font-bold text-ink">서류 스캔 자동분류 확인</h1>
          <p className="text-pc-xs text-subtle">스캔된 서류를 근로자·서류 유형으로 자동 매칭한 뒤 확인합니다</p>
        </div>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-6">
          {stage === 'idle' && (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
              }}
              className="flex flex-1 flex-col items-center justify-center gap-4 rounded-card border border-dashed border-line bg-surface p-10"
            >
              <span className="flex size-14 items-center justify-center rounded-in bg-approvalbg">
                <IconDoc width={26} height={26} className="text-primary" />
              </span>
              <div className="flex flex-col items-center gap-1 text-center">
                <span className="text-label1 font-semibold text-ink">여권·계약서·증명서 스캔 파일을 끌어다 놓거나 선택하세요</span>
                <span className="text-caption1 text-muted">지원 형식: JPG · PNG · PDF</span>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.pdf"
                multiple
                aria-label="스캔 파일 선택"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.length) onFiles(e.target.files);
                  e.target.value = '';
                }}
              />
              <Button variant="primary" onClick={() => fileInputRef.current?.click()}>
                파일 선택
              </Button>
            </div>
          )}

          {stage === 'classifying' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
              <div className="flex w-full max-w-lg flex-col gap-2.5">
                <div className="mb-1 flex items-center gap-2.5">
                  <span className="size-4 shrink-0 rounded-full bg-primary" />
                  <span className="text-label1 font-semibold text-ink">{results.length}개 파일을 분류하는 중</span>
                </div>
                {['90%', '78%', '85%', '70%'].map((w, i) => (
                  <Skeleton key={i} className="h-3.5" style={{ width: w }} />
                ))}
              </div>
              <span className="text-caption1 text-muted">근로자·서류 유형을 매칭하고 있어요</span>
            </div>
          )}

          {stage === 'review' && (
            <>
              <div className="flex gap-1.5">
                {(['all', 'matched', 'low_confidence', 'unmatched'] as Filter[]).map((key) => {
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

              <div className="flex-1 overflow-y-auto rounded-in border border-hairline">
                <div className="grid grid-cols-[92px_1fr_150px_130px_70px_110px] border-b border-hairline bg-surface">
                  {['미리보기', '파일', '매칭된 근로자', '서류 유형', '신뢰도', '상태'].map((h) => (
                    <span key={h} className="px-3 py-1.5 text-pc-2xs font-semibold text-muted">{h}</span>
                  ))}
                </div>
                {visibleResults.map((result) => {
                  const editable = result.status !== 'matched';
                  const pickerOpen = openRowId === result.fileId;
                  return (
                    <div key={result.fileId} className="grid grid-cols-[92px_1fr_150px_130px_70px_110px] border-b border-hairline last:border-none">
                      <span className="p-2"><ScanThumbnail /></span>
                      <span className="flex items-center px-3 py-2 text-pc-xs text-subtle">{result.fileName}</span>
                      <span className="flex items-center px-3 py-2">
                        {editable ? (
                          <button
                            type="button"
                            onClick={() => setOpenRowId(pickerOpen ? null : result.fileId)}
                            className={cn(
                              'flex w-full items-center justify-between gap-1.5 rounded-badge px-2.5 py-1.5 text-caption1 font-semibold transition-colors duration-btn ease-v2',
                              result.status === 'unmatched' && !result.workerName ? 'bg-critbg text-critical' : 'bg-surface text-ink',
                            )}
                          >
                            {result.workerName ?? '지정 필요'}
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="shrink-0"><path d="M6 9l6 6l6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          </button>
                        ) : (
                          <span className="text-pc-sm font-semibold text-ink">{result.workerName}</span>
                        )}
                      </span>
                      <span className="flex items-center px-3 py-2 text-pc-xs text-muted">{result.docType ?? '지정 필요'}</span>
                      <span className="flex items-center px-3 py-2 text-pc-xs text-subtle">{result.status === 'matched' ? '높음' : result.status === 'low_confidence' ? '낮음' : '—'}</span>
                      <span className="flex items-center px-3 py-2">
                        <Chip tone={STATUS_TONE[result.status]}>{STATUS_LABEL[result.status]}</Chip>
                      </span>
                      {pickerOpen && (
                        <CorrectionPanel
                          result={result}
                          workerOptions={workers.map((w) => w.workerRef!.displayName)}
                          onPickWorker={(name) => {
                            const picked = workers.find((w) => w.workerRef?.displayName === name);
                            updateResult(result.fileId, { workerName: name, caseId: picked?.caseId });
                          }}
                          onPickDocType={(docType) => updateResult(result.fileId, { docType })}
                          onClose={() => setOpenRowId(null)}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {stage === 'done' && (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-succbg">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M6 12.5L10.5 17L18 7.5" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" className="text-success" />
                </svg>
              </span>
              <p className="text-body1 font-bold text-ink">{results.length}건이 확인 대기로 올라갔습니다</p>
              <p className="text-caption1 leading-relaxed text-muted">
                자동으로 수령 완료 처리되지 않습니다.
                <br />
                케이스 서류 상태에서 최종 확인해 주세요.
              </p>
              <Button variant="outline" className="mt-1" onClick={reset}>
                다시 업로드
              </Button>
            </div>
          )}
        </div>

        {stage === 'review' ? (
          <div className="flex items-center justify-between gap-4 border-t border-hairline px-6 py-3">
            <span className="text-pc-2xs text-muted">
              {blocked ? '미매칭 건에 근로자를 지정해야 진행할 수 있습니다' : '정상 매칭·확인 필요 건도 함께 확인 대기로 올라갑니다'}
            </span>
            <div className="flex shrink-0 gap-2">
              <Button variant="outline" size="sm" onClick={onCancel}>취소</Button>
              <Button variant="primary" size="sm" onClick={confirmPending} disabled={blocked}>확인 대기로 올리기</Button>
            </div>
          </div>
        ) : (
          stage !== 'done' && (
            <div className="flex items-center justify-center gap-1.5 border-t border-hairline px-6 py-2.5">
              <IconLock width={11} height={11} className="text-subtle" />
              <span className="text-pc-2xs text-muted">개인정보는 DB에만 저장되고, LLM/RAG에 전달되지 않습니다.</span>
            </div>
          )
        )}
      </section>

      <aside aria-label="스캔 안내" className="flex w-[340px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-hairline bg-canvas p-4">
        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">마스킹 안내</span>
          <div className="flex gap-2 rounded-in bg-surface p-3">
            <IconLock width={14} height={14} className="mt-0.5 shrink-0 text-subtle" />
            <span className="text-pc-xs leading-relaxed text-muted">
              미리보기에서 외국인등록번호 등 식별정보 영역은 항상 가려집니다. 원문은 표시되지 않습니다.
            </span>
          </div>
        </section>

        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">상태 기준</span>
          <div className="flex flex-col gap-1.5">
            {(['matched', 'low_confidence', 'unmatched'] as ScanMatchStatus[]).map((status) => (
              <div key={status} className="flex gap-2">
                <Chip tone={STATUS_TONE[status]} className="mt-0.5 shrink-0">{STATUS_LABEL[status]}</Chip>
                <span className="text-pc-xs leading-relaxed text-ink">
                  {status === 'matched' && '근로자·서류 유형을 높은 신뢰도로 매칭했습니다'}
                  {status === 'low_confidence' && '매칭했지만 신뢰도가 낮아 확인이 필요합니다'}
                  {status === 'unmatched' && '근로자를 찾지 못했습니다 · 직접 지정이 필요합니다'}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-2">
          <span className="text-caption1 font-bold tracking-wide text-muted">확인 대기란</span>
          <div className="rounded-in bg-surface p-3">
            <span className="text-pc-xs leading-relaxed text-muted">
              "확인 대기로 올리기"는 케이스 서류 상태를 확인 대기로 전환할 뿐, 자동으로 수령 완료 처리하지 않습니다. 최종 확인은 담당자가 케이스에서 진행합니다.
            </span>
          </div>
        </section>

        <div className="mt-auto rounded-in bg-surface px-2.5 py-2 text-pc-2xs text-muted">
          가능/불가능 판단은 제공하지 않습니다.
        </div>
      </aside>
    </section>
  );
}
