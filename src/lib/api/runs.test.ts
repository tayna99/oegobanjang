import { afterEach, describe, expect, it, vi } from 'vitest';
import { streamCommandRun } from './runs';
import { useSessionStore } from '@/stores/sessionStore';

// backend/app/api/v1/runs.py의 _sse() 포맷("event: X\ndata: Y\n\n")과 1:1로 맞춘다.
function sseBody(frames: { event: string; data: unknown }[]): string {
  return frames.map((f) => `event: ${f.event}\ndata: ${JSON.stringify(f.data)}\n\n`).join('');
}

function makeStreamResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(stream, { status });
}

async function collect<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const item of gen) out.push(item);
  return out;
}

describe('lib/api/runs.streamCommandRun', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
    useSessionStore.getState().reset();
  });

  it('SSE 프레임 시퀀스를 순서대로 파싱하고 POST 요청을 검증한다', async () => {
    // backend/app/api/v1/runs.py의 _event_stream이 frame.pop("type")한 나머지를 그대로 SSE
    // data로 보낸다 — run_service.py가 yield하는 {"type":"step","step":{...}}는 pop 후
    // {"step":{...}}가 되므로, step/structured는 각각 step/data 키로 한 번 더 감싸여 온다
    // (run_created/route/error/done은 flat).
    const body = sseBody([
      { event: 'run_created', data: { run_id: 'run_1' } },
      { event: 'step', data: { step: { kind: 'tool_call', label: '검색', detail: '근거 검색 중' } } },
      {
        event: 'structured',
        data: {
          data: {
            answer: { final_response: '답변', citations: [], missing_evidence: false, risk_flags: [] },
            approval: null,
          },
        },
      },
      { event: 'done', data: { run_id: 'run_1', status: 'completed' } },
    ]);
    const mockFetch = vi.fn().mockResolvedValue(makeStreamResponse([body]));
    global.fetch = mockFetch as unknown as typeof fetch;

    const frames = await collect(streamCommandRun({ companyId: 'cmp1', message: '질문' }));

    expect(frames).toEqual([
      { type: 'run_created', run_id: 'run_1' },
      { type: 'step', step: { kind: 'tool_call', label: '검색', detail: '근거 검색 중' } },
      {
        type: 'structured',
        data: {
          answer: { final_response: '답변', citations: [], missing_evidence: false, risk_flags: [] },
          approval: null,
        },
      },
      { type: 'done', run_id: 'run_1', status: 'completed' },
    ]);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/runs/stream',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ company_id: 'cmp1', message: '질문' }),
      }),
    );
  });

  it('청크가 프레임 경계 중간에서 잘려도(버퍼링) 올바르게 파싱한다', async () => {
    const raw = sseBody([{ event: 'run_created', data: { run_id: 'run_2' } }]);
    const splitPoint = Math.floor(raw.length / 2);
    const mockFetch = vi.fn().mockResolvedValue(makeStreamResponse([raw.slice(0, splitPoint), raw.slice(splitPoint)]));
    global.fetch = mockFetch as unknown as typeof fetch;

    const frames = await collect(streamCommandRun({ companyId: 'cmp1', message: '질문' }));
    expect(frames).toEqual([{ type: 'run_created', run_id: 'run_2' }]);
  });

  it('세션 토큰이 있으면 Authorization 헤더에 싣는다', async () => {
    useSessionStore.setState({ token: 'tok_abc' });
    const mockFetch = vi
      .fn()
      .mockResolvedValue(makeStreamResponse([sseBody([{ event: 'done', data: { run_id: 'r', status: 'completed' } }])]));
    global.fetch = mockFetch as unknown as typeof fetch;

    await collect(streamCommandRun({ companyId: 'cmp1', message: 'x' }));

    expect(mockFetch).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer tok_abc' }) }),
    );
  });

  it('non-ok 응답(403 등)은 JSON detail을 담아 즉시 에러를 던진다 — SSE로 파싱 시도하지 않는다', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '해당 사업장 접근 권한이 없습니다' }), { status: 403 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(collect(streamCommandRun({ companyId: 'cmp1', message: 'x' }))).rejects.toThrow(
      '해당 사업장 접근 권한이 없습니다',
    );
  });
});
