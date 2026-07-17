import { apiFetch } from './client';
import type { MembershipRole } from '@/stores/sessionStore';

// 인증 API 어댑터(R2.2, NEXT_ROADMAP 2.2) — 순수 fetch+DTO 변환만 한다. 스토어 반영은
// lib/auth.ts의 useAuthActions()가 오케스트레이션한다(lib/approval.ts와 동일한 분리 원칙).

export interface AuthUser {
  id: string;
  name: string;
  phone: string;
}

export interface OtpRequestResult {
  requested: boolean;
  expiresInSeconds: number;
  debugCode: string | null; // local 환경 백엔드에서만 채워진다.
}

export interface VerifyOtpResult {
  token: string;
  expiresAt: string;
  user: AuthUser;
}

export interface MembershipResult {
  companyId: string;
  role: MembershipRole;
}

export interface MeResult {
  user: AuthUser;
  membership: MembershipResult | null;
}

interface OtpRequestResponseDto {
  requested: boolean;
  expires_in_seconds: number;
  debug_code: string | null;
}

interface OtpVerifyResponseDto {
  session_token: string;
  expires_at: string;
  user: AuthUser;
}

interface MeResponseDto {
  user: AuthUser;
  membership: { company_id: string; role: MembershipRole } | null;
}

export async function requestOtp(phone: string): Promise<OtpRequestResult> {
  const dto = await apiFetch<OtpRequestResponseDto>('/api/v1/auth/otp/request', {
    method: 'POST',
    body: JSON.stringify({ phone }),
  });
  return { requested: dto.requested, expiresInSeconds: dto.expires_in_seconds, debugCode: dto.debug_code };
}

export async function verifyOtp(phone: string, code: string): Promise<VerifyOtpResult> {
  const dto = await apiFetch<OtpVerifyResponseDto>('/api/v1/auth/otp/verify', {
    method: 'POST',
    body: JSON.stringify({ phone, code }),
  });
  return { token: dto.session_token, expiresAt: dto.expires_at, user: dto.user };
}

// 로그인 사용자 + 활성 소속 — 프론트 roleStore를 세션에서 파생시키는 유일한 근거.
export async function fetchMe(): Promise<MeResult> {
  const dto = await apiFetch<MeResponseDto>('/api/v1/auth/me');
  return {
    user: dto.user,
    membership: dto.membership ? { companyId: dto.membership.company_id, role: dto.membership.role } : null,
  };
}

export async function logout(): Promise<void> {
  await apiFetch<void>('/api/v1/auth/logout', { method: 'POST' });
}
