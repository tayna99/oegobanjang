import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'outline';
export type ButtonSize = 'default' | 'sm';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

// Montage(Wanted) 버튼 규칙 이식(rules/design.md v2 §4) — pri→primary, sec→secondary, line→outline.
// outline은 CSS border 대신 inset box-shadow(레이아웃 시프트 방지, 2026-07-11 M2.5.2).
const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-white active:bg-primary-press disabled:bg-surface disabled:text-faint',
  secondary: 'bg-surface text-ink active:bg-surface-press',
  outline: 'bg-canvas shadow-outline text-ink active:bg-surface-dim',
};

// 라디우스는 Montage "버튼 8~12px 사이즈별" 규칙에 맞춰 사이즈마다 다르다
// (default=10px 공용 입력 반경 재사용, sm=8px 전용 토큰).
const SIZE_CLASSES: Record<ButtonSize, string> = {
  default: 'h-btn text-btn rounded-in',
  sm: 'h-btn-sm text-sm rounded-btn-sm',
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
        'inline-flex items-center justify-center gap-btn-gap px-btn-x font-semibold transition-colors duration-btn ease-v2 disabled:cursor-default',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...props}
    />
  );
}
