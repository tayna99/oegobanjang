import { Badge } from '@/components/Badge';
import { threadBadge } from '@/lib/threads';
import type { MessageThread } from '@/types';

interface ThreadListItemProps {
  thread: MessageThread;
  onOpen: () => void;
  /** offline 상태의 "캐시 리스트(읽기 전용)" — false면 행을 탭할 수 없다. */
  interactive?: boolean;
}

// 공용 컴포넌트가 아니다(domain 타입 MessageThread를 직접 받음) — rules/frontend.md
// "공용(components/)은 도메인 타입 import 금지" 때문에 features/messages/ 안에 둔다.
export function ThreadListItem({ thread, onOpen, interactive = true }: ThreadListItemProps) {
  const badge = threadBadge(thread);
  const initial = thread.workerRef.displayName.charAt(0).toUpperCase();

  const content = (
    <>
      {/* 아바타 42px, radius 14(원형 금지), surface 배경 + 이니셜 muted — 탭별기획 §3.2. 사진 없음(PII 최소화) */}
      <span
        aria-hidden="true"
        className="flex size-[42px] shrink-0 items-center justify-center rounded-chip bg-surface text-sm font-bold text-muted"
      >
        {initial}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline gap-1.5">
          <span className="truncate text-sm font-semibold text-ink">{thread.workerRef.displayName}</span>
          {/* 국적·채널은 정보로만 — 색·국기 강조 금지(가드레일) */}
          <span className="shrink-0 text-tabbar-label font-semibold text-faint">
            {thread.workerRef.nationality} · {thread.channelLabel}
          </span>
        </span>
        {/* 근로자 원문 절대 노출 금지 — thread.preview는 이미 상태 요약 문장 */}
        <span className="mt-0.5 block truncate text-safety text-muted">{thread.preview}</span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1.5">
        {thread.reminderScheduledLabel ? (
          <span className="text-xs font-medium text-info">{thread.reminderScheduledLabel}</span>
        ) : (
          <time className="text-xs text-faint">{thread.timeLabel}</time>
        )}
        <Badge tone={badge.tone}>{badge.label}</Badge>
      </span>
    </>
  );

  if (!interactive) {
    return (
      <div className="flex w-full items-start gap-3 border-b border-surface py-3.5">{content}</div>
    );
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={thread.workerRef.displayName}
      className="flex w-full items-start gap-3 border-b border-surface py-3.5 text-left active:bg-surface-dim"
    >
      {content}
    </button>
  );
}
