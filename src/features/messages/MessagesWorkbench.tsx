import { useEffect, useState } from 'react';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { severityTone } from '@/lib/chipTone';
import { cn } from '@/lib/cn';
import { dDayLabel } from '@/lib/dday';
import { useNav } from '@/lib/nav';
import { CASE_CARDS } from '@/mocks/fixtures';
import { THREAD_LIST, threadFor, type MessageThread, type ThreadMessage } from '@/mocks/messages';
import { canTransition, useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

// PC 메시지(4c) — reference/design-system/외고반장 PC_4a-4f(신규티어).dc.html §4c(240~349행)
// 부분 구현. M6 해석확인 로직은 ThreadPage(모바일)와 같은 규칙(evidence + 합법 전이만 상태
// 반영)을 이 화면에서 독립적으로 구현한다 — CaseWorkbench(PC)/CaseReviewPage(모바일) 관계와
// 동일하게 "공유 데이터층, 플랫폼별 별도 프레젠테이션" 원칙(JSX를 억지로 공유하지 않는다).
const LANG_LABEL: Record<string, string> = { vi: '베트남어', id: '인도네시아어', en: '영어', ko: '한국어' };

function Bubble({ message }: { message: ThreadMessage }) {
  const mine = message.sender !== 'worker';
  return (
    <div className={cn('flex flex-col gap-0.5', mine ? 'items-end' : 'items-start')}>
      <div className={cn('max-w-[75%] rounded-card px-3.5 py-2.5 text-pc-sm leading-relaxed', mine ? 'bg-approvalbg text-ink' : 'bg-surface text-ink')}>
        {message.lang && message.lang !== 'ko' && (
          <span className="mb-1 inline-block text-pc-2xs font-bold text-approval">{LANG_LABEL[message.lang]} 원문</span>
        )}
        <p>{message.text}</p>
      </div>
      <span className="px-1 text-pc-2xs text-dim">{message.at}</span>
    </div>
  );
}

export function MessagesWorkbench() {
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const [selectedId, setSelectedId] = useState(THREAD_LIST[0]?.threadId);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);
  const [confirmedIds, setConfirmedIds] = useState<Set<string>>(() => {
    const seeded = new Set<string>();
    for (const t of THREAD_LIST) {
      if (useEvidenceStore.getState().events.some((e) => e.id === `${t.caseId}-interpretation-confirmed`)) {
        seeded.add(t.threadId);
      }
    }
    return seeded;
  });

  const thread: MessageThread | undefined = threadFor(selectedId);
  const linkedCase = thread ? cases[thread.caseId] : undefined;
  const confirmed = thread ? confirmedIds.has(thread.threadId) : false;

  const onConfirm = () => {
    if (!thread) return;
    appendEvidence({
      id: `${thread.caseId}-interpretation-confirmed`,
      type: 'final_response_generated',
      at: new Date().toISOString(),
      caseId: thread.caseId,
      summary: `${thread.workerName} 응답 해석 확인 — 상태 업데이트 반영`,
      actor: '김담당',
    });
    const current = useCaseStore.getState().cases[thread.caseId];
    if (current && canTransition(current.state, 'approval_pending')) {
      useCaseStore.getState().transition(thread.caseId, 'approval_pending');
    }
    setConfirmedIds((prev) => new Set(prev).add(thread.threadId));
  };

  return (
    <section aria-label="메시지 워크벤치" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <nav aria-label="스레드 목록" className="flex w-[280px] shrink-0 flex-col overflow-y-auto border-r border-hairline bg-canvas">
        {THREAD_LIST.map((t) => (
          <button
            key={t.threadId}
            type="button"
            aria-pressed={t.threadId === selectedId}
            onClick={() => setSelectedId(t.threadId)}
            className={cn(
              'flex flex-col gap-0.5 border-b border-hairline px-3.5 py-3 text-left transition-colors duration-btn ease-v2',
              t.threadId === selectedId ? 'bg-approvalbg shadow-rail-active' : 'hover:bg-surface',
            )}
          >
            <span className="flex items-center gap-2">
              <span className="truncate text-pc-sm font-semibold text-ink">{t.workerName}</span>
              <span className="shrink-0 text-pc-2xs text-dim">{t.channel}</span>
            </span>
            <span className="truncate text-pc-2xs text-subtle">{t.listLabel}</span>
          </button>
        ))}
        <p className="mt-auto px-3.5 py-3 text-pc-2xs leading-relaxed text-faint">
          행정사와의 소통은 패키지 회신으로 — 이 채널에 포함되지 않습니다.
        </p>
      </nav>

      <section className="flex min-w-0 flex-1 flex-col bg-canvas">
        {!thread ? (
          <p className="p-6 text-body2 text-muted">대화를 선택하세요</p>
        ) : (
          <>
            <header className="border-b border-hairline px-6 pb-3 pt-4">
              <h1 className="text-body1 font-bold text-ink">{thread.workerName}</h1>
              <p className="text-pc-xs text-subtle">{thread.team} · {thread.channel}</p>
            </header>
            <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-6">
              {thread.messages.map((m) => (
                <Bubble key={m.id} message={m} />
              ))}
              {thread.interpretation && (
                <section aria-label="응답 해석" className="mt-2 flex flex-col gap-2 rounded-card border border-hairline p-3.5">
                  <div className="flex items-center gap-2">
                    <Chip tone="draft">AI 해석</Chip>
                    {!thread.interpretation.isFinal && !confirmed && <Chip tone="high">담당자 확인 필요</Chip>}
                    {confirmed && <Chip tone="positive">확인됨</Chip>}
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-pc-2xs font-bold text-subtle">한국어 요약</span>
                    <p className="text-pc-sm leading-relaxed text-ink">{thread.interpretation.koSummary}</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-pc-2xs font-bold text-subtle">상태 업데이트 제안</span>
                    <p className="text-pc-sm leading-relaxed text-muted">{thread.interpretation.proposal}</p>
                  </div>
                  {!confirmed ? (
                    <Button variant="primary" size="sm" className="mt-1 self-start" onClick={onConfirm}>
                      해석 확인 · 상태 반영
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" className="mt-1 self-start" onClick={() => nav.toCase(thread.caseId)}>
                      케이스 열기
                    </Button>
                  )}
                  <p className="text-pc-2xs text-faint">해석 확인 없이 상태가 자동 변경되지 않습니다.</p>
                </section>
              )}
            </div>
            <footer className="flex justify-center border-t border-hairline px-6 py-2">
              <p className="text-pc-2xs text-subtle">승인 전에는 외부 발송이 차단됩니다.</p>
            </footer>
          </>
        )}
      </section>

      <aside aria-label="연결 케이스" className="flex w-[300px] shrink-0 flex-col gap-3 overflow-y-auto border-l border-hairline bg-canvas p-4">
        <span className="text-caption1 font-bold tracking-wide text-muted">연결 케이스</span>
        {linkedCase ? (
          <div className="flex flex-col gap-2 rounded-card border border-hairline p-3.5">
            <div className="flex flex-wrap gap-1.5">
              <Chip tone={severityTone(linkedCase.severity)}>
                {linkedCase.severity}
                {linkedCase.dDay !== undefined ? ` · ${dDayLabel(linkedCase.dDay)}` : ''}
              </Chip>
            </div>
            <p className="text-pc-sm font-semibold text-ink">{linkedCase.title}</p>
            <Button variant="outline" size="sm" onClick={() => nav.toCase(linkedCase.caseId)}>
              케이스 열기
            </Button>
          </div>
        ) : (
          <p className="text-pc-xs text-muted">연결된 케이스가 없습니다.</p>
        )}
      </aside>
    </section>
  );
}
