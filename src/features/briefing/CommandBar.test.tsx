import type { ReactElement } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { CommandBar } from './CommandBar';

function RunIdProbe() {
  const { runId } = useParams<{ runId: string }>();
  return <div>런 화면 · runId:{runId}</div>;
}

function renderWithRunRoute(ui: ReactElement) {
  render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={ui} />
        <Route path="/run/:runId" element={<RunIdProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CommandBar', () => {
  it('placeholder 문구를 보여준다', () => {
    render(
      <MemoryRouter>
        <CommandBar />
      </MemoryRouter>,
    );
    expect(screen.getByPlaceholderText('AI에게 요청하기')).toBeInTheDocument();
  });

  it('매칭되는 워커명이 없으면 입력값을 비우고 기본 command 런(#4797)으로 이동한다', () => {
    renderWithRunRoute(<CommandBar />);
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '이번 달 급한 직원만 정리해줘' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.getByText('런 화면 · runId:4797')).toBeInTheDocument();
    expect(input.value).toBe('');
  });

  // R1.6 — 입력→런 매핑: 워커명이 포함되면 그 워커의 실제 승인 런으로 바로 연결한다.
  it('입력에 워커명이 포함되면 그 워커의 승인 런으로 연결한다', () => {
    renderWithRunRoute(<CommandBar />);
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Nguyen 씨한테 서류 요청 보내줘' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.getByText('런 화면 · runId:nguyen')).toBeInTheDocument();
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

  // R1.6 — 추천 칩은 입력창만 채우지 않고 즉시 제출한다.
  it('추천 칩을 누르면 즉시 제출되어 런 화면으로 이동한다', () => {
    renderWithRunRoute(<CommandBar suggestions={['오늘 승인 대기 요약해줘']} />);
    fireEvent.click(screen.getByText('오늘 승인 대기 요약해줘'));
    expect(screen.getByText('런 화면 · runId:4797')).toBeInTheDocument();
  });
});
