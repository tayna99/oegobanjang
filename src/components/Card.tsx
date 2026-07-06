import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export type CardVariant = 'default' | 'hero';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  interactive?: boolean;
}

// 프로토타입 v3 .card 클래스 이식. hero는 보더 없이 그림자만(동시 사용 금지 규칙, rules/design.md).
const VARIANT_CLASSES: Record<CardVariant, string> = {
  default: 'border border-hairline',
  hero: 'shadow-card',
};

export function Card({ variant = 'default', interactive = false, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-card bg-canvas p-5',
        VARIANT_CLASSES[variant],
        interactive && 'cursor-pointer transition-shadow duration-fast active:shadow-lift',
        className,
      )}
      {...props}
    />
  );
}
