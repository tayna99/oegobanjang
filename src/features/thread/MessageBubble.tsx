import { cn } from '@/lib/cn';
import { formatClockTime } from '@/lib/threads';
import type { Message } from '@/types';

export interface MessageBubbleProps {
  message: Message;
}

// 대화 타임라인 버블 — reference/prototype_v3.html 202~206행 .bub/.bubmeta 이식.
// out(담당자→근로자)=우측 정렬 surface 필, in(근로자→담당자)=좌측 정렬 흰+hairline.
// out 메타는 v3 913행 형식 그대로: "승인 후 발송됨 · 판단 기록 {ref} · {시각}".
// evidenceRef는 out(발송된 메시지)에만 표시한다 — in 메시지는 판단 기록을 만들지 않는다.
export function MessageBubble({ message }: MessageBubbleProps) {
  const isOut = message.direction === 'out';
  const time = formatClockTime(message.at);

  const meta = isOut
    ? message.deliveryStatus === 'sent' && message.evidenceRef
      ? `승인 후 발송됨 · 판단 기록 ${message.evidenceRef} · ${time}`
      : time
    : `${time} · 수신`;

  return (
    <div className={cn('mb-3.5 max-w-[82%]', isOut ? 'ml-auto' : 'mr-auto')}>
      <p
        className={cn(
          'whitespace-pre-line rounded-card px-4 py-3.5 text-sm leading-relaxed',
          isOut ? 'rounded-br-md bg-surface text-ink' : 'rounded-bl-md border border-hairline bg-canvas text-ink',
        )}
      >
        {message.body}
      </p>
      <p className={cn('mt-1.5 text-xs text-faint', isOut && 'text-right')}>{meta}</p>
    </div>
  );
}
