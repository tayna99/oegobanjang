import { useState } from 'react';
import { Button } from '@/components/Button';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Skeleton } from '@/components/Skeleton';
import { formatClockTime, formatDateCaption, latestInboundMessage } from '@/lib/threads';
import type { Interpretation, Message, MessageThread } from '@/types';
import { InterpretationCard } from './InterpretationCard';
import { MessageBubble } from './MessageBubble';

// 1단계 스펙 §M6 "상태 5종" — default 안에 interpretation/timeline 2모드가 있다
// (탭별기획 §3.3 "승인 대기→M3 직행 / 응답도착→M6 / 완료→대화 타임라인" 3분기 중
// 뒤 2개가 이 컴포넌트 몫. 첫 번째는 ThreadPage가 <Navigate>로 처리).
export type ThreadViewState =
  | { status: 'default'; mode: 'interpretation'; thread: MessageThread; interpretation: Interpretation }
  | { status: 'default'; mode: 'timeline'; thread: MessageThread }
  | { status: 'empty'; thread: MessageThread }
  | { status: 'loading'; thread: MessageThread }
  | { status: 'error'; thread: MessageThread }
  | { status: 'offline'; thread: MessageThread; interpretation: Interpretation; lastSyncedAt: string };

export interface ThreadScreenProps {
  state: ThreadViewState;
  onConfirm: (updateIds: string[]) => void;
  onRetry?: () => void;
  onNewDraft?: () => void;
  confirmDisabled?: boolean;
}

// 확인 전 하단 고정 캡션 — v3 918행 원문 그대로.
const PRE_CONFIRM_CAPTION = '확인 전에는 상태가 확정되지 않습니다';
// 타임라인 하단 고정 캡션 — 메시지 탭과 동일 스펙 문구(GOTCHAS: 고정 문구 그대로).
const SEND_CAPTION = '모든 메시지는 승인 후에만 발송됩니다';

function ResponseHeader({ thread, atIso }: { thread: MessageThread; atIso?: string }) {
  return (
    <header className="mb-4">
      <h1 className="text-xl font-bold text-ink">
        {thread.interpretationStatus === 'pending_review' ? '응답 도착 · ' : ''}
        {thread.workerRef.displayName}
      </h1>
      <p className="mt-0.5 text-sm text-faint">
        {thread.channelLabel}
        {atIso && ` · ${formatClockTime(atIso)} 수신`}
      </p>
    </header>
  );
}

// 원문 — 접힌 상태 기본, 탭하면 펼침. 원문 접근은 절대 막지 않는다(1단계 §M6).
function OriginalMessage({ message }: { message: Message }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setExpanded((v) => !v)}
      className="mb-4 w-full rounded-card border border-hairline bg-canvas px-4 py-3.5 text-left"
    >
      <span className="flex items-center justify-between text-xs font-semibold text-muted">
        원문
        <span className="text-faint">{expanded ? '접기' : '펼치기'}</span>
      </span>
      {expanded && <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink">{message.body}</p>}
    </button>
  );
}

function TimelineBody({ thread }: { thread: MessageThread }) {
  let lastCaption = '';
  return (
    <div>
      {thread.messages.map((message) => {
        const caption = formatDateCaption(message.at);
        const showCaption = caption !== lastCaption;
        lastCaption = caption;
        return (
          <div key={message.messageId}>
            {showCaption && <p className="my-4 text-center text-xs text-faint">{caption}</p>}
            <MessageBubble message={message} />
          </div>
        );
      })}
      {thread.interpretationStatus === 'confirmed' && thread.interpretation?.confirmedCardText && (
        <div className="mb-3.5 rounded-card bg-surface p-4 text-sm text-ink">
          {thread.interpretation.confirmedCardText}
        </div>
      )}
    </div>
  );
}

export function ThreadScreen({ state, onConfirm, onRetry, onNewDraft, confirmDisabled }: ThreadScreenProps) {
  if (state.status === 'loading') {
    const inbound = latestInboundMessage(state.thread);
    return (
      <div className="p-5">
        <ResponseHeader thread={state.thread} atIso={inbound?.at} />
        {inbound && <OriginalMessage message={inbound} />}
        <div className="rounded-card bg-surface p-4" aria-hidden="true">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="mt-3 h-4 w-full" />
          <Skeleton className="mt-2 h-4 w-3/4" />
        </div>
        <p className="mt-3 text-sm text-muted">AI가 응답을 해석하고 있습니다</p>
      </div>
    );
  }

  if (state.status === 'error') {
    const inbound = latestInboundMessage(state.thread);
    return (
      <div className="p-5">
        <ResponseHeader thread={state.thread} atIso={inbound?.at} />
        {inbound && <OriginalMessage message={inbound} />}
        <p className="text-sm text-critical-text">요약에 실패했습니다</p>
        <Button variant="outline" className="mt-3" onClick={onRetry}>
          다시 시도
        </Button>
      </div>
    );
  }

  if (state.status === 'offline') {
    const inbound = latestInboundMessage(state.thread);
    return (
      <div>
        <OfflineBanner lastSyncedAt={state.lastSyncedAt} />
        <div className="p-5">
          <ResponseHeader thread={state.thread} atIso={inbound?.at} />
          {inbound && <OriginalMessage message={inbound} />}
          <InterpretationCard interpretation={state.interpretation} onConfirm={onConfirm} confirmDisabled />
        </div>
      </div>
    );
  }

  if (state.status === 'empty') {
    return (
      <div className="p-5">
        <ResponseHeader thread={state.thread} />
        <div className="mt-4 rounded-card border border-hairline bg-canvas p-5 text-center">
          <p className="text-sm text-muted">아직 응답이 없습니다</p>
          <p className="mt-1 text-sm text-faint">메시지가 발송되면 이곳에 대화가 표시됩니다</p>
        </div>
      </div>
    );
  }

  // status === 'default'
  if (state.mode === 'interpretation') {
    const inbound = latestInboundMessage(state.thread);
    return (
      <div className="p-5 pb-8">
        <ResponseHeader thread={state.thread} atIso={inbound?.at} />
        {inbound && <OriginalMessage message={inbound} />}
        <InterpretationCard
          interpretation={state.interpretation}
          onConfirm={onConfirm}
          confirmDisabled={confirmDisabled}
        />
        <p className="mt-3 text-center text-xs text-faint">{PRE_CONFIRM_CAPTION}</p>
      </div>
    );
  }

  // mode === 'timeline'
  const canDraft = Boolean(state.thread.caseId);
  return (
    <div className="flex min-h-full flex-col">
      <div className="flex-1 p-5 pb-4">
        <ResponseHeader thread={state.thread} />
        <TimelineBody thread={state.thread} />
      </div>
      <div className="sticky bottom-0 border-t border-hairline bg-canvas p-4">
        <Button
          variant="secondary"
          className="w-full"
          disabled={!canDraft}
          onClick={onNewDraft}
        >
          새 메시지 초안 만들기
        </Button>
        <p className="mt-2 text-center text-safety text-faint">{SEND_CAPTION}</p>
      </div>
    </div>
  );
}
