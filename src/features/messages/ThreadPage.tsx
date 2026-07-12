import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { BackHeader } from '@/components/BackHeader';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { cn } from '@/lib/cn';
import { useNav } from '@/lib/nav';
import { threadFor, type ThreadMessage } from '@/mocks/messages';
import { useEvidenceStore } from '@/stores/evidenceStore';

// 스레드 대화 뷰 + M6 응답 해석(2.2) — 원문은 여기(스레드 내부)에서만 노출.
// M6: 근로자 회신 → 원문 + KR 요약 + 상태 업데이트 제안. isFinal:false면 "해석 확인" 후 반영
// (담당자 확인 필요). 확인 시 evidence(final_response_generated) 기록 — 자동 상태 변경은 하지 않는다.

const LANG_LABEL: Record<string, string> = { vi: '베트남어', id: '인도네시아어', en: '영어', ko: '한국어' };

function Bubble({ message }: { message: ThreadMessage }) {
  const mine = message.sender !== 'worker';
  return (
    <div className={cn('flex flex-col gap-0.5', mine ? 'items-end' : 'items-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-card px-3.5 py-2.5 text-label1 leading-relaxed',
          mine ? 'bg-approvalbg text-ink' : 'bg-surface text-ink',
        )}
      >
        {message.lang && message.lang !== 'ko' && (
          <span className="mb-1 inline-block text-pc-2xs font-bold text-approval">{LANG_LABEL[message.lang]} 원문</span>
        )}
        <p className={cn(message.lang && message.lang !== 'ko' && 'block')}>{message.text}</p>
      </div>
      <span className="px-1 text-pc-2xs text-dim">{message.at}</span>
    </div>
  );
}

export function ThreadPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const nav = useNav();
  const thread = threadFor(threadId);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const [confirmed, setConfirmed] = useState(false);

  // 이미 확인된 해석이면(evidence 존재) 확인 상태로 시작.
  useEffect(() => {
    if (!thread) return;
    const id = `${thread.caseId}-interpretation-confirmed`;
    if (useEvidenceStore.getState().events.some((e) => e.id === id)) setConfirmed(true);
  }, [thread]);

  if (!thread) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">대화를 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toMessages()}>
          메시지로
        </Button>
      </div>
    );
  }

  const interp = thread.interpretation;

  const onConfirm = () => {
    // isFinal:false 해석을 담당자가 확인 → 상태 갱신 반영 + evidence(자동 변경 아님, 사람 확인).
    appendEvidence({
      id: `${thread.caseId}-interpretation-confirmed`,
      type: 'final_response_generated',
      at: new Date().toISOString(),
      caseId: thread.caseId,
      summary: `${thread.workerName} 응답 해석 확인 — 상태 업데이트 반영`,
      actor: '김담당',
    });
    setConfirmed(true);
  };

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title={thread.workerName} onBack={() => nav.toMessages()} />

      <main className="flex flex-1 flex-col gap-4 px-5 pb-28 pt-4">
        <p className="text-center text-caption1 text-dim">
          {thread.team} · {thread.channel}
        </p>

        <div className="flex flex-col gap-3">
          {thread.messages.map((message) => (
            <Bubble key={message.id} message={message} />
          ))}
        </div>

        {interp && (
          <section aria-label="응답 해석" className="flex flex-col gap-2 rounded-card border border-hairline bg-canvas p-3.5">
            <div className="flex items-center gap-2">
              <Chip tone="draft">AI 해석</Chip>
              {!interp.isFinal && !confirmed && <Chip tone="high">담당자 확인 필요</Chip>}
              {confirmed && <Chip tone="positive">확인됨</Chip>}
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-caption1 font-bold text-subtle">한국어 요약</span>
              <p className="text-label1 leading-relaxed text-ink">{interp.koSummary}</p>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-caption1 font-bold text-subtle">상태 업데이트 제안</span>
              <p className="text-label1 leading-relaxed text-muted">{interp.proposal}</p>
            </div>
            {!confirmed ? (
              <Button variant="primary" size="sm" className="mt-1 w-full" onClick={onConfirm}>
                해석 확인 · 상태 반영
              </Button>
            ) : (
              <Button variant="outline" size="sm" className="mt-1 w-full" onClick={() => nav.toCase(thread.caseId)}>
                케이스 열기
              </Button>
            )}
          </section>
        )}
      </main>

      <footer className="fixed inset-x-0 bottom-0 border-t border-hairline bg-canvas px-5 py-3">
        <p className="text-center text-caption1 text-subtle">승인 전에는 외부 발송이 차단됩니다.</p>
      </footer>
    </div>
  );
}
