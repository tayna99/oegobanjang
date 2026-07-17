import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from './client';

// R2.1 DoD — API 클라이언트 계층: 기본 URL 호출·JSON 파싱·에러 매핑·빈 본문 처리.
describe('apiFetch', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('기본 API_BASE_URL로 요청하고 JSON 응답을 파싱한다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ hello: 'world' }), { status: 200 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await apiFetch<{ hello: string }>('/api/v1/health');

    expect(result).toEqual({ hello: 'world' });
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/health', expect.objectContaining({ headers: expect.any(Headers) }));
  });

  it('본문이 있으면 Content-Type을 자동으로 채운다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    await apiFetch('/api/v1/x', { method: 'POST', body: JSON.stringify({ a: 1 }) });

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json');
  });

  it('비2xx 응답은 ApiError(status, body)로 던진다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: '잘못된 요청' }), { status: 422 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const error = await apiFetch('/api/v1/x').catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(422);
    expect((error as ApiError).body).toEqual({ detail: '잘못된 요청' });
  });

  it('빈 본문 응답(예: 204)은 undefined를 반환한다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await apiFetch('/api/v1/logout', { method: 'POST' });
    expect(result).toBeUndefined();
  });
});
