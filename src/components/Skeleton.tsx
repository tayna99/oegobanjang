import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export type SkeletonProps = HTMLAttributes<HTMLDivElement>;

// Skeleton — Montage 공용 컴포넌트.dc.html §5(2.5.4b): pulse 단색 대신 shimmer 그라데이션
// (1.6s ease infinite, 스프링 없음). 크기/모양은 호출부 className이 결정한다.
// .skeleton-shimmer는 src/index.css @layer utilities 정의(reduced-motion 시 정지).
export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn('skeleton-shimmer rounded-in', className)}
      aria-hidden="true"
      {...props}
    />
  );
}
