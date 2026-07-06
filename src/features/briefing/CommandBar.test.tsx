import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CommandBar } from './CommandBar';

describe('CommandBar', () => {
  it('placeholder 문구를 보여준다', () => {
    render(<CommandBar />);
    expect(screen.getByPlaceholderText('AI에게 요청하기')).toBeInTheDocument();
  });

  it('제출하면 입력값을 비운다(런 엔진 연결 전까지는 UI만)', () => {
    render(<CommandBar />);
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '이번 달 급한 직원만 정리해줘' } });
    fireEvent.submit(input.closest('form')!);
    expect(input.value).toBe('');
  });

  it('suggestions가 있으면 칩으로 보여준다(최대 3개)', () => {
    render(<CommandBar suggestions={['서류 누락 확인', '이번 주 만료 확인']} />);
    expect(screen.getByText('서류 누락 확인')).toBeInTheDocument();
    expect(screen.getByText('이번 주 만료 확인')).toBeInTheDocument();
  });
});
