import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.2 DoD — 실 API 모드에서 O1이 실제 OTP 왕복으로 세션·역할을 확립한다.
// USE_REAL_API를 모듈 목으로 켠다(vi.mock은 파일 전체에 호이스트되어 이 파일의 모든
// import — client.ts를 경유하는 것까지 — 가 동일하게 관측한다).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', USE_REAL_API: true }));

import { StepPhoneAuth } from './StepPhoneAuth';
import { useRoleStore } from '@/stores/roleStore';
import { useSessionStore } from '@/stores/sessionStore';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

describe('StepPhoneAuth — 실 API 모드(R2.2)', () => {
  afterEach(() => {
    useSessionStore.getState().clear();
    useRoleStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('전화번호가 실제 입력 가능하고, OTP 요청→검증 성공 시 세션·역할이 반영된다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ requested: true, expires_in_seconds: 300, debug_code: '123456' }))
      .mockResolvedValueOnce(
        jsonResponse({
          session_token: 'tok1',
          expires_at: '2026-08-01T00:00:00Z',
          user: { id: 'u1', name: '김담당', phone: '010-0000-0001' },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          user: { id: 'u1', name: '김담당', phone: '010-0000-0001' },
          membership: { company_id: 'cmp1', role: 'manager' },
        }),
      );
    global.fetch = fetchMock as unknown as typeof fetch;

    const onCodeConfirmedChange = vi.fn();
    render(<StepPhoneAuth onCodeConfirmedChange={onCodeConfirmedChange} />);

    const phoneInput = screen.getByRole('textbox', { name: '휴대폰 번호' }) as HTMLInputElement;
    expect(phoneInput.value).toBe('010-0000-0001');

    fireEvent.click(screen.getByRole('button', { name: '인증번호 받기' }));
    await waitFor(() => expect(screen.getByText(/데모 코드: 123456/)).toBeInTheDocument());

    fireEvent.change(screen.getByRole('textbox', { name: '인증번호 6자리' }), { target: { value: '123456' } });

    await waitFor(() => expect(onCodeConfirmedChange).toHaveBeenLastCalledWith(true));
    expect(useSessionStore.getState().token).toBe('tok1');
    expect(useSessionStore.getState().membership).toEqual({ companyId: 'cmp1', role: 'manager' });
    expect(useRoleStore.getState().role).toBe('manager');
  });

  it('검증 실패 시 세션을 확립하지 않고 오류 문구를 보여준다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ requested: true, expires_in_seconds: 300, debug_code: '999999' }))
      .mockResolvedValueOnce(jsonResponse({ detail: '코드가 일치하지 않습니다' }, 401));
    global.fetch = fetchMock as unknown as typeof fetch;

    const onCodeConfirmedChange = vi.fn();
    render(<StepPhoneAuth onCodeConfirmedChange={onCodeConfirmedChange} />);

    fireEvent.click(screen.getByRole('button', { name: '인증번호 받기' }));
    await waitFor(() => expect(screen.getByText(/데모 코드: 999999/)).toBeInTheDocument());

    fireEvent.change(screen.getByRole('textbox', { name: '인증번호 6자리' }), { target: { value: '000000' } });

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('인증번호가 올바르지 않습니다.'));
    expect(useSessionStore.getState().token).toBeNull();
    expect(onCodeConfirmedChange).toHaveBeenLastCalledWith(false);
  });
});
