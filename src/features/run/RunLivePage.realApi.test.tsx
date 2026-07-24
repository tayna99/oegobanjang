import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R4.1 — API_MODE를 모듈 목으로 'real'로 켠다(ApprovePage.realApi.test.tsx와 동일 관례).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { RunLivePage } from './RunLivePage';
import { useSessionStore } from '@/stores/sessionStore';

function sseBody(frames: { event: string; data: unknown }[]): string {
  return frames.map((f) => `event: ${f.event}\ndata: ${JSON.stringify(f.data)}\n\n`).join('');
}

function makeStreamResponse(body: string, status = 200): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(body));
      controller.close();
    },
  });
  return new Response(stream, { status });
}

function renderAt(entry: { pathname: string; state?: unknown }) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/run/live" element={<RunLivePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RunLivePage — real 모드(R4.1)', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
    useSessionStore.getState().reset();
  });

  it('location.state에 message가 없으면(직접 진입·새로고침) 안내 문구를 보여준다', () => {
    renderAt({ pathname: '/run/live' });
    expect(screen.getByText(/진행 중인 요청 정보를 찾을 수 없습니다/)).toBeInTheDocument();
  });

  it('message가 있으면 실 SSE 런을 시작해 스텝·답변·근거를 렌더한다', async () => {
    useSessionStore.setState({ companyId: 'cmp1' });
    // backend/app/api/v1/runs.py가 frame.pop("type") 후 나머지를 SSE data로 보내므로
    // step/structured는 각각 step/data 키로 한 번 더 감싸여 온다(runs.test.ts와 동일 계약).
    const body = sseBody([
      { event: 'step', data: { step: { kind: 'tool_call', label: '근거 검색', detail: null } } },
      {
        event: 'structured',
        data: {
          data: {
            answer: {
              final_response: '체류연장에는 여권 사본과 근로계약서가 필요합니다.',
              citations: [{ source_id: 'cit_1', title: '체류연장 절차 안내', evidence_grade: 'A' }],
              missing_evidence: false,
              risk_flags: [],
            },
            approval: null,
          },
        },
      },
      { event: 'done', data: { run_id: 'r1', status: 'completed' } },
    ]);
    const mockFetch = vi.fn().mockResolvedValue(makeStreamResponse(body));
    global.fetch = mockFetch as unknown as typeof fetch;

    renderAt({ pathname: '/run/live', state: { message: '체류연장 서류 뭐 필요해' } });

    await waitFor(() =>
      expect(screen.getByText('체류연장에는 여권 사본과 근로계약서가 필요합니다.')).toBeInTheDocument(),
    );
    expect(screen.getByText(/A등급 · 체류연장 절차 안내/)).toBeInTheDocument();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/runs/stream',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ company_id: 'cmp1', message: '체류연장 서류 뭐 필요해' }),
      }),
    );
  });
});
