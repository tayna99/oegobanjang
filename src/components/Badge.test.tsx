import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge } from './Badge';
import type { BadgeTone } from '@/lib/badgeTone';

describe('Badge 색 규칙', () => {
  it.each([
    ['critical', 'bg-critbg', 'text-critical-text'],
    ['warning', 'bg-warnbg', 'text-warning-text'],
    ['pending', 'bg-pendbg', 'text-pending'],
    ['info', 'bg-infobg', 'text-info'],
    ['success', 'bg-succbg', 'text-success'],
    ['neutral', 'bg-neutbg', 'text-neutral'],
    ['line', 'bg-canvas', 'text-muted'],
  ] as const)('%s 톤은 %s / %s 클래스를 갖는다', (tone, bgClass, textClass) => {
    const { getByText } = render(<Badge tone={tone as BadgeTone}>라벨</Badge>);
    const badge = getByText('라벨');
    expect(badge).toHaveClass(bgClass);
    expect(badge).toHaveClass(textClass);
  });

  it('line 톤은 border-hairline 테두리를 갖는다', () => {
    const { getByText } = render(<Badge tone="line">라인</Badge>);
    expect(getByText('라인')).toHaveClass('border', 'border-hairline');
  });

  it('children 텍스트를 그대로 렌더한다', () => {
    const { getByText } = render(<Badge tone="info">D-3</Badge>);
    expect(getByText('D-3')).toBeInTheDocument();
  });
});
