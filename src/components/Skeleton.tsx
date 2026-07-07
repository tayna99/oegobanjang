import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export type SkeletonProps = HTMLAttributes<HTMLDivElement>;

// rules/design.md "스켈레톤 #e5e8ef 블록, 카드 기하 유지" — 크기/모양은 호출부 className이 결정한다.
export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn('animate-pulse rounded-in bg-hairline motion-reduce:animate-none', className)}
      aria-hidden="true"
      {...props}
    />
  );
}
