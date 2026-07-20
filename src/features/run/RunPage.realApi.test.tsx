import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// SD-4 — API_MODE를 'real'로 모듈 목(ApprovePage.realApi.test.tsx·dataSeed.realApi.test.ts와
// 동일 관례). RunPage가 RUN_CONFIGS에 없는 runId를 real 모드에서 liveRunStore로 렌더하는지
// 검증한다. 핸드오프 설계(CommandBar가 스트림을 열고 run_created 도착 시 liveRunStore에 심음,
// RunPage는 재구독만)를 fetch 레벨에서 통째로 검증하기 위해 실제 streamCommandRun 경로를 쓴다
// (liveRunStore.test.ts는 streamCommandRun을 목으로 대체해 스토어 로직만 보는 반면, 여기서는
// "POST가 한 번만 나가는가"까지 확인하는 것이 핵심이므로 fetch를 직접 목한다).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { RunPage } from './RunPage';
import { useLiveRunStore } from '@/stores/liveRunStore';
import { useSessionStore } from '@/stores/sessionStore';

function sseChunk(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/run/:runId" element={<RunPage />} />
        <Route path="/done" element={<div>완료 화면</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RunPage — real 모드 실시간 커맨드 런(SD-4)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    useLiveRunStore.getState().reset();
    useSessionStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('CommandBar가 이미 시작해 둔 실시간 런을 다시 열지 않고 이어받아 렌더한다(핸드오프 설계)', async () => {
    useSessionStore.setState({ companyId: 'cmp1', token: 'tok1' });
    const full =
      sseChunk('run_created', { run_id: 'run_live_1' }) +
      sseChunk('route', { route: { should_run: true, intent: 'visa_expiry' } }) +
      sseChunk('step', { step: { kind: 'thinking', label: '판별 중', detail: 'D-day 계산' } }) +
      sseChunk('structured', {
        data: {
          answer: { final_response: '비자 만료 임박 케이스 2건입니다.', citations: [], missing_evidence: false, risk_flags: [] },
          approval: { required: true, status: 'PENDING', blocked_actions: [], reason: '' },
        },
      }) +
      sseChunk('done', { run_id: 'run_live_1', status: 'waiting_approval', approval_required: true });
    const fetchMock = vi.fn().mockResolvedValue(new Response(full));
    global.fetch = fetchMock as unknown as typeof fetch;

    // CommandBar를 렌더하지 않고 스토어 진입점을 직접 호출한다 — 이 테스트의 관심사는
    // "RunPage가 스트림을 다시 여는가"이지 CommandBar의 제출 UI 자체가 아니다(그건 아래
    // CommandBar.realApi.test.tsx가 담당).
    const runId = await useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: '비자 만료 확인해줘' });
    expect(runId).toBe('run_live_1');

    renderAt(`/run/${runId}`);

    expect(await screen.findByText('비자 만료 확인해줘')).toBeInTheDocument(); // title = 원문 커맨드
    await waitFor(() => expect(screen.getByText('판별 중')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('비자 만료 임박 케이스 2건입니다.')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole('button', { name: '승인' })).toBeEnabled());

    // 스트림을 시작한 것은 startCommandRun 1회뿐 — RunPage 마운트가 두 번째 POST를 만들지 않는다.
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: '승인' }));
    expect(await screen.findByText('완료 화면')).toBeInTheDocument();
  });

  it('차단된 라우팅(should_run=false)은 에러 화면으로 렌더한다', async () => {
    useSessionStore.setState({ companyId: 'cmp1' });
    const full =
      sseChunk('run_created', { run_id: 'run_blocked' }) +
      sseChunk('route', { route: { should_run: false, intent: 'forbidden' } }) +
      sseChunk('done', { run_id: 'run_blocked', status: 'completed' });
    global.fetch = vi.fn().mockResolvedValue(new Response(full)) as unknown as typeof fetch;

    const runId = await useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: '국적별로 추천해줘' });
    renderAt(`/run/${runId}`);

    expect(await screen.findByText(/지원 범위 밖입니다/)).toBeInTheDocument();
  });

  it('liveRunStore에 없는 runId는 real 모드에서도 재요청 안내를 보여준다(무한 loading 아님)', () => {
    renderAt('/run/never-started');
    expect(screen.getByText(/이 런을 찾을 수 없습니다/)).toBeInTheDocument();
  });
});
