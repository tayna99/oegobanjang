import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// VITE_API_BASE_URL이 설정된 상태로 모듈을 매번 새로 로드해야 apiEnabled=true가 된다
// (모듈 스코프 상수라 import 시점에 한 번만 평가됨) — vi.resetModules + dynamic import.
async function loadApi() {
  vi.stubEnv('VITE_API_BASE_URL', 'http://api.test');
  vi.resetModules();
  return import('./api');
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('api.decideApproval', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('apiEnabled reflects VITE_API_BASE_URL presence', async () => {
    const api = await loadApi();
    expect(api.apiEnabled).toBe(true);
  });

  it('resolves case→approval via caseCode and posts the decision with the session token', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ debug_code: '123456' })) // otp/request
      .mockResolvedValueOnce(jsonResponse({ session_token: 'tok-abc' })) // otp/verify
      .mockResolvedValueOnce(new Response(null, { status: 204 })) // auth/pin
      .mockResolvedValueOnce(jsonResponse({ cases: [{ id: 'cs_nguyen', case_code: 'case_002' }] })) // cases
      .mockResolvedValueOnce(jsonResponse({ approvals: [{ id: 'apv_nguyen', status: 'pending' }] })) // approvals
      .mockResolvedValueOnce(jsonResponse({ approval: { id: 'apv_nguyen' }, case_state: 'human_approved' }));

    const api = await loadApi();
    await api.decideApproval({ caseCode: 'case_002', decision: 'approved', idempotencyKey: 'key-1' });

    expect(fetchMock).toHaveBeenCalledTimes(6);
    const decideCall = fetchMock.mock.calls[5];
    expect(decideCall[0]).toBe('http://api.test/api/v1/approvals/apv_nguyen/approve');
    const init = decideCall[1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok-abc');
    const body = JSON.parse(init.body as string);
    expect(body).toMatchObject({ idempotency_key: 'key-1', identity_method: 'pin', pin_code: '000000' });
  });

  it('throws ApiError when the case has no pending approval', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ debug_code: '123456' }))
      .mockResolvedValueOnce(jsonResponse({ session_token: 'tok-abc' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse({ cases: [{ id: 'cs_x', case_code: 'case_009' }] }))
      .mockResolvedValueOnce(jsonResponse({ approvals: [] }));

    const api = await loadApi();
    await expect(
      api.decideApproval({ caseCode: 'case_009', decision: 'approved', idempotencyKey: 'k' }),
    ).rejects.toThrow(api.ApiError);
  });

  it('propagates non-2xx decide responses as ApiError with the status code', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ debug_code: '123456' }))
      .mockResolvedValueOnce(jsonResponse({ session_token: 'tok-abc' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse({ cases: [{ id: 'cs_x', case_code: 'case_002' }] }))
      .mockResolvedValueOnce(jsonResponse({ approvals: [{ id: 'apv_1', status: 'pending' }] }))
      .mockResolvedValueOnce(new Response('근거가 없어 승인할 수 없습니다', { status: 422 }));

    const api = await loadApi();
    try {
      await api.decideApproval({ caseCode: 'case_002', decision: 'approved', idempotencyKey: 'k' });
      throw new Error('expected rejection');
    } catch (err) {
      expect(err).toBeInstanceOf(api.ApiError);
      expect((err as InstanceType<typeof api.ApiError>).status).toBe(422);
    }
  });
});
