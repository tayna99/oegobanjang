import type { ReactNode } from 'react';
import type { ChipTone } from '@/lib/chipTone';
import { cn } from '@/lib/cn';

export interface ChipProps {
  tone: ChipTone;
  children: ReactNode;
  className?: string;
}

// Montage(Wanted) Chip 규칙(rules/design.md v2 §4·5) — v1 Badge에서 개명(M2.5.2).
// radius 8px(--r-chip, Montage Chip 6~10 범위), padding 3px 8px, gap 5px 유지.
// 'line' 톤은 CSS border 대신 inset box-shadow(레이아웃 시프트 방지 규칙).
const TONE_CLASSES: Record<ChipTone, string> = {
  critical: 'bg-critbg text-critical',
  high: 'bg-warnbg text-warning',
  medium: 'bg-medbg text-medium',
  positive: 'bg-succbg text-success',
  approval: 'bg-approvalbg text-approval',
  neutral: 'bg-neutbg text-neutral',
  line: 'bg-canvas shadow-outline text-muted',
};

export function Chip({ tone, children, className }: ChipProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-badge-gap rounded-badge py-badge-y px-2 text-xs font-semibold leading-normal transition-shadow duration-chip ease-v2',
        TONE_CLASSES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
