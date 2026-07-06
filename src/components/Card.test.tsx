import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Card } from './Card';

describe('Card', () => {
  it('default variant는 border-hairline을 렌더하고 shadow-card는 없다', () => {
    const { container } = render(<Card>내용</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('border-hairline');
    expect(card.className).not.toContain('shadow-card');
  });

  it('hero variant는 shadow-card를 렌더하고 border-hairline은 없다', () => {
    const { container } = render(<Card variant="hero">내용</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('shadow-card');
    expect(card.className).not.toContain('border-hairline');
  });

  it('interactive=true면 cursor-pointer가 추가된다', () => {
    const { container } = render(<Card interactive>내용</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('cursor-pointer');
  });

  it('interactive가 false거나 생략되면 cursor-pointer가 없다', () => {
    const { container: withFalse } = render(<Card interactive={false}>내용</Card>);
    expect((withFalse.firstChild as HTMLElement).className).not.toContain('cursor-pointer');

    const { container: withOmitted } = render(<Card>내용</Card>);
    expect((withOmitted.firstChild as HTMLElement).className).not.toContain('cursor-pointer');
  });

  it('children을 렌더한다', () => {
    render(<Card>카드 본문</Card>);
    expect(screen.getByText('카드 본문')).toBeInTheDocument();
  });

  it('onClick이 전달되면 클릭 시 호출된다', async () => {
    const handleClick = vi.fn();
    render(<Card onClick={handleClick}>클릭 카드</Card>);
    screen.getByText('클릭 카드').click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
