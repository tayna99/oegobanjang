import { afterEach, describe, expect, it, vi } from 'vitest';
import { streamCommandRun } from './runs';
import { useSessionStore } from '@/stores/sessionStore';

// SD-4 — dataSeed.realApi.test.ts와 동일 관례(global.fetch 목)로, 여기서는 fetch가
// text/event-stream ReadableStream을 돌려주는 상황을 직접 시뮬레이션한다. EventSource를
// 쓸 수 없는 이유(POST+Authorization 헤더)는 lib/api/runs.ts 모듈 주석 참조.

function sseChunk(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

// 프레임을 즉시 다 밀어넣지 않고 test가 원하는 타이밍에 하나씩 enqueue할 수 있게 하는
// 제어형 스트림 — cancel()이 "이미 버퍼에 도착한 다음 프레임"을 처리하지 않는지 검증하려면
// 한 번에 다 보내면 안 된다(즉시 완료돼 버려 취소 타이밍을 잡을 수 없다).
function controlledStream() {
  let controllerRef: ReadableStreamDefaultController<Uint8Array> | null = null;
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      controllerRef = c;
    },
  });
  return {
    stream,
    push: (text: string) => controllerRef?.enqueue(encoder.encode(text)),
    close: () => controllerRef?.close(),
  };
}

function flush(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe('streamCommandRun — SSE 어댑터(SD-4)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    useSessionStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('run_created → step → structured → done 프레임을 순서대로 콜백에 전달한다', async () => {
    const full =
      sseChunk('run_created', { run_id: 'run_1' }) +
      sseChunk('route', { route: { should_run: true, intent: 'visa_expiry' } }) +
      sseChunk('step', { step: { kind: 'thinking', label: '판별 중', detail: 'D-day 계산' } }) +
      sseChunk('step', { step: { kind: 'tool_call', label: '근거 조회', detail: '3건' } }) +
      sseChunk('structured', {
        data: {
          answer: { final_response: '체류만료가 임박했습니다.', citations: [], missing_evidence: false, risk_flags: [] },
          approval: { required: true, status: 'PENDING', blocked_actions: [], reason: '' },
        },
      }) +
      sseChunk('done', { run_id: 'run_1', status: 'waiting_approval', approval_required: true });

    global.fetch = vi.fn().mockResolvedValue(new Response(full)) as unknown as typeof fetch;

    const onRunCreated = vi.fn();
    const onRoute = vi.fn();
    const onStep = vi.fn();
    const onStructured = vi.fn();
    const onDone = vi.fn();

    streamCommandRun(
      { companyId: 'cmp1', message: '비자 만료 확인해줘' },
      { onRunCreated, onRoute, onStep, onStructured, onDone },
    );

    await flush();
    await flush();

    expect(onRunCreated).toHaveBeenCalledWith('run_1');
    expect(onRoute).toHaveBeenCalledWith({ should_run: true, intent: 'visa_expiry' });
    expect(onStep).toHaveBeenNthCalledWith(1, { kind: 'thinking', label: '판별 중', detail: 'D-day 계산' });
    expect(onStep).toHaveBeenNthCalledWith(2, { kind: 'tool_call', label: '근거 조회', detail: '3건' });
    expect(onStructured).toHaveBeenCalledWith({
      answer: { final_response: '체류만료가 임박했습니다.', citations: [], missing_evidence: false, risk_flags: [] },
      approval: { required: true, status: 'PENDING', blocked_actions: [], reason: '' },
    });
    expect(onDone).toHaveBeenCalledWith({ run_id: 'run_1', status: 'waiting_approval', approval_required: true });

    const [url, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:8000/api/v1/runs/stream');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({
      company_id: 'cmp1',
      message: '비자 만료 확인해줘',
      thread_id: null,
    });
  });

  it('차단된 라우팅(should_run=false)은 route+done만 오고 structured는 오지 않는다', async () => {
    const full =
      sseChunk('run_created', { run_id: 'run_2' }) +
      sseChunk('route', { route: { should_run: false, intent: 'forbidden' } }) +
      sseChunk('done', { run_id: 'run_2', status: 'completed' });

    global.fetch = vi.fn().mockResolvedValue(new Response(full)) as unknown as typeof fetch;

    const onRoute = vi.fn();
    const onStructured = vi.fn();
    const onDone = vi.fn();

    streamCommandRun({ companyId: 'cmp1', message: '국적별로 추천해줘' }, { onRoute, onStructured, onDone });

    await flush();
    await flush();

    expect(onRoute).toHaveBeenCalledWith({ should_run: false, intent: 'forbidden' });
    expect(onStructured).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledWith({ run_id: 'run_2', status: 'completed' });
  });

  it('error 프레임이 오면 onError로 전달하고 이후 프레임은 없다', async () => {
    const full = sseChunk('run_created', { run_id: 'run_3' }) + sseChunk('error', { detail: 'rag 서비스 실패' });
    global.fetch = vi.fn().mockResolvedValue(new Response(full)) as unknown as typeof fetch;

    const onError = vi.fn();
    const onDone = vi.fn();
    streamCommandRun({ companyId: 'cmp1', message: 'x' }, { onError, onDone });

    await flush();
    await flush();

    expect(onError).toHaveBeenCalledWith('rag 서비스 실패');
    expect(onDone).not.toHaveBeenCalled();
  });

  it('응답이 실패(비 2xx)면 onError로 상태코드를 전달한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: '권한 없음' }), { status: 403 })) as unknown as typeof fetch;

    const onError = vi.fn();
    streamCommandRun({ companyId: 'cmp1', message: 'x' }, { onError });

    await flush();

    expect(onError).toHaveBeenCalledWith(expect.stringContaining('403'));
  });

  it('토큰이 있으면 Authorization 헤더를 싣는다', async () => {
    useSessionStore.setState({ token: 'tok_abc' });
    global.fetch = vi.fn().mockResolvedValue(new Response(sseChunk('run_created', { run_id: 'run_4' }))) as unknown as typeof fetch;

    streamCommandRun({ companyId: 'cmp1', message: 'x' }, {});
    await flush();

    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok_abc');
  });

  it('cancel()을 호출하면 그 이후 도착한 프레임은 처리하지 않는다', async () => {
    const { stream, push, close } = controlledStream();
    global.fetch = vi.fn().mockResolvedValue(new Response(stream)) as unknown as typeof fetch;

    const onStep = vi.fn();
    const handle = streamCommandRun({ companyId: 'cmp1', message: 'x' }, { onStep });

    push(sseChunk('run_created', { run_id: 'run_5' }));
    await flush();
    push(sseChunk('step', { step: { kind: 'thinking', label: '1', detail: '' } }));
    await flush();
    expect(onStep).toHaveBeenCalledTimes(1);

    handle.cancel();
    push(sseChunk('step', { step: { kind: 'thinking', label: '2', detail: '' } }));
    await flush();
    close();
    await flush();

    expect(onStep).toHaveBeenCalledTimes(1); // 취소 후 두 번째 스텝은 소비되지 않는다.
  });
});
