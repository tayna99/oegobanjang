import { useEffect, useState } from 'react';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { severityTone } from '@/lib/chipTone';
import { cn } from '@/lib/cn';
import { useSeedCases, useSeedThreadDetail, useSeedThreads } from '@/lib/dataSeed';
import { dDayLabel } from '@/lib/dday';
import { useConfirmInterpretation } from '@/lib/interpretation';
import { useNav } from '@/lib/nav';
import { formatClockTime, sortThreads } from '@/lib/threads';
import { useCaseStore } from '@/stores/caseStore';
import { useThreadStore } from '@/stores/threadStore';
import type { Message, MessageThread } from '@/types';

// PC 메시지(4c) — reference/design-system/외고반장 PC_4a-4f(신규티어).dc.html §4c(240~349행)
// 부분 구현. NEXT_ROADMAP D-1(2026-07-17)로 독립 mock(mocks/messages.ts)을 폐기하고
// threadStore/mocks/threads.ts(모바일과 동일한 데이터 소스)로 재배선 — 모바일·PC가 이제
// 같은 스레드를 본다. M6 해석확인 오케스트레이션(evidence + 합법 전이만 상태 반영)은
// ThreadPage(모바일)와 lib/interpretation.ts의 useConfirmInterpretation 공유 훅을 함께
// 쓴다(코드리뷰 reuse 지적으로 통합 — 이전엔 두 화면이 같은 로직을 각자 재구현했다).
// 그래도 프레젠테이션(JSX)은 CaseWorkbench(PC)/CaseReviewPage(모바일) 관계와 동일하게
// 플랫폼별로 분리 유지한다("공유 데이터층·오케스트레이션, 플랫폼별 프레젠테이션").
const LANG_LABEL: Record<string, string> = { vi: '베트남어', id: '인도네시아어', en: '영어', ko: '한국어', mn: '몽골어' };

function Bubble({ message }: { message: Message }) {
  const mine = message.direction === 'out';
  return (
    <div className={cn('flex flex-col gap-0.5', mine ? 'items-end' : 'items-start')}>
      <div className={cn('max-w-[75%] rounded-card px-3.5 py-2.5 text-pc-sm leading-relaxed', mine ? 'bg-approvalbg text-ink' : 'bg-surface text-ink')}>
        {message.lang !== 'ko' && (
          <span className="mb-1 inline-block text-pc-2xs font-bold text-approval">{LANG_LABEL[message.lang] ?? message.lang} 원문</span>
        )}
        <p className="whitespace-pre-line">{message.body}</p>
      </div>
      <span className="px-1 text-pc-2xs text-dim">{formatClockTime(message.at)}</span>
    </div>
  );
}

export function MessagesWorkbench() {
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const threads = useThreadStore((s) => s.threads);
  const confirmInterpretationFor = useConfirmInterpretation();
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

  useSeedCases();
  useSeedThreads();

  useEffect(() => {
    // 초기 선택은 딱 한 번만 정한다 — sorted[0]을 매 렌더 폴백으로 쓰면, 지금 보고 있는
    // 스레드의 해석을 확인해 pending_review에서 빠지는 순간 정렬이 바뀌어 화면이 다른
    // 스레드로 조용히 튀어버린다(확인 직후 아직 열려 있어야 할 대화가 사라지는 버그).
    setSelectedId((prev) => prev ?? sortThreads(Object.values(useThreadStore.getState().threads))[0]?.threadId);
  }, []);

  const sorted = sortThreads(Object.values(threads));
  const activeId = selectedId ?? sorted[0]?.threadId;

  useSeedThreadDetail(activeId);

  const thread: MessageThread | undefined = activeId ? threads[activeId] : undefined;
  // 아직 발송 전(draftCaseId만 있는) 스레드도 "연결 케이스"는 보여준다 — 발송 여부와
  // 무관하게 이 대화가 어떤 케이스에 속하는지는 항상 의미가 있다.
  const linkedCaseId = thread?.caseId ?? thread?.draftCaseId;
  const linkedCase = linkedCaseId ? cases[linkedCaseId] : undefined;
  const confirmed = thread?.interpretationStatus === 'confirmed';

  const onConfirm = () => {
    if (!thread) return;
    confirmInterpretationFor(thread.threadId);
  };

  return (
    <section aria-label="메시지 워크벤치" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <nav aria-label="스레드 목록" className="flex w-[280px] shrink-0 flex-col overflow-y-auto border-r border-hairline bg-canvas">
        {sorted.map((t) => (
          <button
            key={t.threadId}
            type="button"
            aria-pressed={t.threadId === activeId}
            onClick={() => setSelectedId(t.threadId)}
            className={cn(
              'flex flex-col gap-0.5 border-b border-hairline px-3.5 py-3 text-left transition-colors duration-btn ease-v2',
              t.threadId === activeId ? 'bg-approvalbg shadow-rail-active' : 'hover:bg-surface',
            )}
          >
            <span className="flex items-center gap-2">
              <span className="truncate text-pc-sm font-semibold text-ink">{t.workerRef.displayName}</span>
              <span className="shrink-0 text-pc-2xs text-dim">{t.channelLabel}</span>
            </span>
            {/* 근로자 원문 절대 노출 금지 — preview는 이미 상태 요약 문장(GOTCHAS §3) */}
            <span className="truncate text-pc-2xs text-subtle">{t.preview}</span>
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
              <h1 className="text-body1 font-bold text-ink">{thread.workerRef.displayName}</h1>
              <p className="text-pc-xs text-subtle">{thread.workerRef.nationality} · {thread.channelLabel}</p>
            </header>
            <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-6">
              {thread.draftCaseId && thread.messages.length === 0 ? (
                <div className="rounded-card border border-hairline bg-canvas p-4 text-center">
                  <p className="text-pc-sm text-muted">{thread.preview}</p>
                  <p className="mt-1 text-pc-2xs text-faint">아직 발송되지 않았습니다 — 승인 후 발송됩니다.</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => thread.draftCaseId && nav.toDraft(thread.draftCaseId)}
                  >
                    초안 보기
                  </Button>
                </div>
              ) : (
                thread.messages.map((m) => <Bubble key={m.messageId} message={m} />)
              )}
              {thread.interpretation && (
                <section aria-label="응답 해석" className="mt-2 flex flex-col gap-2 rounded-card border border-hairline p-3.5">
                  <div className="flex items-center gap-2">
                    <Chip tone="draft">AI 해석</Chip>
                    {!confirmed && <Chip tone="approval">담당자 확인 필요</Chip>}
                    {confirmed && <Chip tone="positive">확인됨</Chip>}
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-pc-2xs font-bold text-subtle">한국어 요약</span>
                    <p className="text-pc-sm leading-relaxed text-ink">{thread.interpretation.summaryKo}</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    {thread.interpretation.updates.map((update) => (
                      <p key={update.updateId} className="text-pc-sm leading-relaxed text-muted">
                        <span className="font-semibold text-ink">{update.field}</span>: {update.from} → {update.to}
                      </p>
                    ))}
                  </div>
                  {!confirmed ? (
                    <Button variant="primary" size="sm" className="mt-1 self-start" onClick={onConfirm}>
                      해석 확인 · 상태 반영
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-1 self-start"
                      onClick={() => thread.caseId && nav.toCase(thread.caseId)}
                    >
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
