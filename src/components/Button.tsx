import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'outline';
export type ButtonSize = 'default' | 'sm';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

// 프로토타입 v3 .btn 클래스 이식 — pri→primary, sec→secondary, line→outline.
const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-white active:bg-primary-press disabled:bg-surface disabled:text-faint',
  secondary: 'bg-surface text-ink active:bg-surface-press',
  outline: 'bg-canvas border border-hairline text-ink active:bg-surface-dim',
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  default: 'h-btn text-btn',
  sm: 'h-btn-sm text-sm',
};

export function Button({
  variant = 'primary',
  size = 'default',
  className,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-btn-gap rounded-in px-btn-x font-semibold transition-colors duration-fast disabled:cursor-default',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...props}
    />
  );
}
