import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Button } from './Button';

describe('Button', () => {
  it('기본값(variant=primary, size=default)으로 렌더한다', () => {
    render(<Button>확인</Button>);
    const button = screen.getByRole('button', { name: '확인' });
    expect(button.className).toContain('bg-primary');
    expect(button.className).toContain('h-btn');
  });

  it.each([
    ['primary', 'bg-primary'],
    ['secondary', 'bg-surface'],
    ['outline', 'shadow-outline'],
  ] as const)('variant=%s는 구분 클래스 %s를 포함한다', (variant, expectedClass) => {
    render(<Button variant={variant}>버튼</Button>);
    expect(screen.getByRole('button', { name: '버튼' }).className).toContain(expectedClass);
  });

  it("variant='outline'은 border 클래스를 쓰지 않는다(inset box-shadow, rules/design.md v2 §4)", () => {
    render(<Button variant="outline">버튼</Button>);
    expect(screen.getByRole('button', { name: '버튼' }).className).not.toMatch(/\bborder\b/);
  });

  it("size='sm'은 h-btn-sm 클래스를 렌더한다", () => {
    render(<Button size="sm">작은 버튼</Button>);
    expect(screen.getByRole('button', { name: '작은 버튼' }).className).toContain('h-btn-sm');
  });

  it('children 텍스트를 렌더한다', () => {
    render(<Button>제출하기</Button>);
    expect(screen.getByText('제출하기')).toBeInTheDocument();
  });

  it('클릭 시 onClick이 호출된다', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>클릭</Button>);
    fireEvent.click(screen.getByRole('button', { name: '클릭' }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('disabled면 클릭해도 onClick이 호출되지 않는다', () => {
    const handleClick = vi.fn();
    render(
      <Button onClick={handleClick} disabled>
        비활성
      </Button>,
    );
    fireEvent.click(screen.getByRole('button', { name: '비활성' }));
    expect(handleClick).not.toHaveBeenCalled();
  });
});
