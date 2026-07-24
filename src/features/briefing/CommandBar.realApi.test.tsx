import type { ReactElement } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

// R4.1 — API_MODE를 모듈 목으로 'real'로 켠다(ApprovePage.realApi.test.tsx와 동일 관례).
// mock 모드 회귀 가드는 기존 CommandBar.test.tsx가 그대로 맡는다 — 이 파일은 real 분기만 검증.
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { CommandBar } from './CommandBar';

function LiveRunProbe() {
  const location = useLocation();
  const state = location.state as { message?: string } | null;
  return <div>라이브런 화면 · message:{state?.message ?? ''}</div>;
}

function renderWithLiveRunRoute(ui: ReactElement) {
  render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={ui} />
        <Route path="/run/live" element={<LiveRunProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CommandBar — real 모드(R4.1)', () => {
  it('제출 시 resolveCommandRunKey 대신 /run/live로 message를 실어 이동한다', () => {
    renderWithLiveRunRoute(<CommandBar />);
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '체류연장 서류 뭐 필요해' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.getByText('라이브런 화면 · message:체류연장 서류 뭐 필요해')).toBeInTheDocument();
    expect(input.value).toBe('');
  });

  it('공백만 입력하면 제출하지 않는다(backend message min_length=1 — 422 방지)', () => {
    renderWithLiveRunRoute(<CommandBar />);
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.queryByText(/라이브런 화면/)).not.toBeInTheDocument();
  });
});
