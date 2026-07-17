import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from './client';

describe('apiFetch (R2.1 API 클라이언트 공용 래퍼)', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('성공 응답의 JSON body를 그대로 반환한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiFetch<{ ok: boolean }>('/api/v1/health');
    expect(result).toEqual({ ok: true });
  });

  it('204 No Content는 body 파싱 없이 undefined를 반환한다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const result = await apiFetch<void>('/api/v1/auth/logout', { method: 'POST' });
    expect(result).toBeUndefined();
  });

  it('token이 있으면 Authorization 헤더를 붙인다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/api/v1/auth/me', { token: 'sess-abc' });

    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer sess-abc');
  });

  it('body를 넘기면 JSON.stringify해서 보낸다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/api/v1/auth/otp/request', { method: 'POST', body: { phone: '010-0000-0001' } });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe(JSON.stringify({ phone: '010-0000-0001' }));
  });

  it('실패 응답은 ApiError로 던진다(status 포함)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('세션이 만료됐습니다', { status: 401, statusText: 'Unauthorized' })),
    );

    await expect(apiFetch('/api/v1/auth/me')).rejects.toMatchObject({
      status: 401,
      message: '세션이 만료됐습니다',
    });
  });

  it('ApiError는 Error의 인스턴스다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })));
    try {
      await apiFetch('/api/v1/auth/me');
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err).toBeInstanceOf(Error);
    }
  });
});
