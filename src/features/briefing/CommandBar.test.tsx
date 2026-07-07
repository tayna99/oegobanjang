import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { CommandBar } from './CommandBar';

describe('CommandBar', () => {
  it('placeholder 문구를 보여준다', () => {
    render(
      <MemoryRouter>
        <CommandBar />
      </MemoryRouter>,
    );
    expect(screen.getByPlaceholderText('AI에게 요청하기')).toBeInTheDocument();
  });

  it('제출하면 입력값을 비우고 command 데모 런(#4790)으로 이동한다', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<CommandBar />} />
          <Route path="/run/:runId" element={<div>런 화면</div>} />
        </Routes>
      </MemoryRouter>,
    );
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '이번 달 급한 직원만 정리해줘' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.getByText('런 화면')).toBeInTheDocument();
  });

  it('suggestions가 있으면 칩으로 보여준다(최대 3개)', () => {
    render(
      <MemoryRouter>
        <CommandBar suggestions={['서류 누락 확인', '이번 주 만료 확인']} />
      </MemoryRouter>,
    );
    expect(screen.getByText('서류 누락 확인')).toBeInTheDocument();
    expect(screen.getByText('이번 주 만료 확인')).toBeInTheDocument();
  });
});
