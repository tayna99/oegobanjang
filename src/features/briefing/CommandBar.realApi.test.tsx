import type { ReactElement } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// SD-4 — API_MODE를 'real'로 모듈 목(ApprovePage.realApi.test.tsx와 동일 관례). CommandBar가
// real 모드에서 mock 매핑(resolveCommandRunKey) 대신 실제 POST /runs/stream을 열고,
// run_created 프레임이 도착한 뒤에만 그 runId로 이동하는지 검증한다.
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { CommandBar } from './CommandBar';
import { useLiveRunStore } from '@/stores/liveRunStore';
import { useSessionStore } from '@/stores/sessionStore';

function sseChunk(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

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

describe('CommandBar — real 모드(SD-4)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    useLiveRunStore.getState().reset();
    useSessionStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('제출하면 POST /api/v1/runs/stream을 열고 run_created 프레임 도착 후 그 runId로 이동한다', async () => {
    useSessionStore.setState({ companyId: 'cmp1', token: 'tok1' });
    const full = sseChunk('run_created', { run_id: 'run_live_9' }) + sseChunk('done', { run_id: 'run_live_9', status: 'completed' });
    const fetchMock = vi.fn().mockResolvedValue(new Response(full));
    global.fetch = fetchMock as unknown as typeof fetch;

    renderWithRunRoute(<CommandBar />);
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '이번 주 만료 확인해줘' } });
    fireEvent.submit(input.closest('form')!);

    expect(input.value).toBe(''); // 제출 즉시 입력값은 비워진다(기존 동작과 동일).
    await waitFor(() => expect(screen.getByText('런 화면 · runId:run_live_9')).toBeInTheDocument());

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:8000/api/v1/runs/stream');
    expect(JSON.parse(init.body as string)).toMatchObject({ company_id: 'cmp1', message: '이번 주 만료 확인해줘' });
  });

  it('companyId가 없으면(세션 복원 전) fetch하지 않는다', () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    renderWithRunRoute(<CommandBar />);
    const input = screen.getByPlaceholderText('AI에게 요청하기') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '이번 주 만료 확인해줘' } });
    fireEvent.submit(input.closest('form')!);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
