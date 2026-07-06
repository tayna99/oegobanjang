import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Skeleton } from './Skeleton';

describe('Skeleton', () => {
  it('렌더된다', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('전달된 className이 기본 클래스와 함께 합쳐진다', () => {
    const { container } = render(<Skeleton className="h-4 w-24" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain('h-4');
    expect(el.className).toContain('w-24');
    expect(el.className).toContain('bg-hairline');
    expect(el.className).toContain('animate-pulse');
  });

  it('motion-reduce에서 애니메이션을 끄는 클래스를 포함한다', () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain('motion-reduce:animate-none');
  });

  it('스크린 리더에서 감춰진다(aria-hidden)', () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el).toHaveAttribute('aria-hidden', 'true');
  });
});
