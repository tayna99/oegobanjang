import { apiFetch } from './client';

// R2.2 — backend/app/api/v1/auth.py 어댑터. 백엔드 응답(snake_case)을 프론트 관례(camelCase)로
// 옮기는 경계가 여기 하나뿐이어야 한다(스토어는 이 파일의 타입만 본다).
export interface SessionUser {
  id: string;
  name: string;
  phone: string;
}

export interface Membership {
  companyId: string;
  role: string;
}

export interface OtpRequestResult {
  requested: boolean;
  expiresInSeconds: number;
  debugCode: string | null;
}

export interface OtpVerifyResult {
  sessionToken: string;
  expiresAt: string;
  user: SessionUser;
}

export interface MeResult {
  user: SessionUser;
  memberships: Membership[];
}

interface OtpRequestResponseDto {
  requested: boolean;
  expires_in_seconds: number;
  debug_code: string | null;
}

interface OtpVerifyResponseDto {
  session_token: string;
  expires_at: string;
  user: SessionUser;
}

interface MembershipDto {
  company_id: string;
  role: string;
}

interface MeResponseDto {
  user: SessionUser;
  memberships: MembershipDto[];
}

export async function requestOtp(phone: string): Promise<OtpRequestResult> {
  const dto = await apiFetch<OtpRequestResponseDto>('/api/v1/auth/otp/request', {
    method: 'POST',
    body: { phone },
  });
  return { requested: dto.requested, expiresInSeconds: dto.expires_in_seconds, debugCode: dto.debug_code };
}

export async function verifyOtp(phone: string, code: string): Promise<OtpVerifyResult> {
  const dto = await apiFetch<OtpVerifyResponseDto>('/api/v1/auth/otp/verify', {
    method: 'POST',
    body: { phone, code },
  });
  return { sessionToken: dto.session_token, expiresAt: dto.expires_at, user: dto.user };
}

export async function fetchMe(token: string): Promise<MeResult> {
  const dto = await apiFetch<MeResponseDto>('/api/v1/auth/me', { token });
  return {
    user: dto.user,
    memberships: dto.memberships.map((m) => ({ companyId: m.company_id, role: m.role })),
  };
}

export async function logout(token: string): Promise<void> {
  await apiFetch<void>('/api/v1/auth/logout', { method: 'POST', token });
}
