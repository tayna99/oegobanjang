import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Chip } from './Chip';
import type { ChipTone } from '@/lib/chipTone';

describe('Chip 색 규칙 (v2, rules/design.md §5)', () => {
  it.each([
    ['critical', 'bg-critbg', 'text-critical'],
    ['high', 'bg-warnbg', 'text-warning'],
    ['medium', 'bg-medbg', 'text-medium'],
    ['positive', 'bg-succbg', 'text-success'],
    ['approval', 'bg-approvalbg', 'text-approval'],
    ['neutral', 'bg-neutbg', 'text-neutral'],
    ['line', 'bg-canvas', 'text-muted'],
  ] as const)('%s 톤은 %s / %s 클래스를 갖는다', (tone, bgClass, textClass) => {
    const { getByText } = render(<Chip tone={tone as ChipTone}>라벨</Chip>);
    const chip = getByText('라벨');
    expect(chip).toHaveClass(bgClass);
    expect(chip).toHaveClass(textClass);
  });

  it('line 톤은 border 대신 inset box-shadow(shadow-outline)를 갖는다', () => {
    const { getByText } = render(<Chip tone="line">라인</Chip>);
    expect(getByText('라인')).toHaveClass('shadow-outline');
    expect(getByText('라인').className).not.toMatch(/\bborder\b/);
  });

  it('children 텍스트를 그대로 렌더한다', () => {
    const { getByText } = render(<Chip tone="approval">D-3</Chip>);
    expect(getByText('D-3')).toBeInTheDocument();
  });
});
