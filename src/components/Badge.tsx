import type { ReactNode } from 'react';
import type { BadgeTone } from '@/lib/badgeTone';
import { cn } from '@/lib/cn';

export interface BadgeProps {
  tone: BadgeTone;
  children: ReactNode;
  className?: string;
}

// 배지 색 규칙(1단계 스펙 §0.2) — 프로토타입 v3 .bdg 클래스 그대로 이식
// (reference/prototype_v3.html 47-62행 부근: radius 8px, padding 3px 8px, gap 5px,
// font-size 12px, font-weight 600, line-height 1.5, inline-flex).
// radius는 칩(14px)과 다른 8px(GOTCHAS: 임의값 금지, rounded-badge로 토큰 등록됨).
const TONE_CLASSES: Record<BadgeTone, string> = {
  critical: 'bg-critbg text-critical-text',
  warning: 'bg-warnbg text-warning-text',
  pending: 'bg-pendbg text-pending',
  info: 'bg-infobg text-info',
  success: 'bg-succbg text-success',
  neutral: 'bg-neutbg text-neutral',
  line: 'bg-canvas border border-hairline text-muted',
};

export function Badge({ tone, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-badge-gap rounded-badge py-badge-y px-2 text-xs font-semibold leading-normal',
        TONE_CLASSES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
