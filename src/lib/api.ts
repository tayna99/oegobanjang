/**
 * mockApi → 실 백엔드 어댑터(docs/DB_SCHEMA.md §8 계약 동기화 결정). `VITE_API_BASE_URL`이
 * 없으면 apiEnabled=false — 승인 플로우는 기존 mockApi(zustand store) 그대로 동작한다(회귀 없음).
 *
 * dev 전용 대역: 로그인 화면(M4)·PIN 등록 화면·M2.6 체크리스트 화면이 아직 없어 여기서
 * 자동 로그인(seed owner) + 고정 PIN + 전체 checked 체크리스트로 게이트를 통과시킨다. 실
 * 화면이 붙으면 이 자동화를 걷어내고 그 화면이 실제 값을 넘기도록 교체한다.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL as string | undefined;
export const apiEnabled = Boolean(API_BASE);

// db/seed_demo.sql usr_owner('김대표') — approval_policy가 owner_only/manager_allowed
// 어느 쪽이든 owner는 항상 결정 가능해 dev 자동 로그인 대상으로 가장 안전하다.
const DEV_LOGIN_PHONE = (import.meta.env.VITE_DEV_LOGIN_PHONE as string | undefined) ?? '010-0000-0003';
const DEV_PIN = '000000';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

let sessionToken: string | null = null;
let sessionReady: Promise<void> | null = null;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new ApiError(resp.status, detail || resp.statusText);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

function ensureSession(): Promise<void> {
  if (sessionToken) return Promise.resolve();
  if (!sessionReady) {
    sessionReady = (async () => {
      const otpReq = await request<{ debug_code: string | null }>('/api/v1/auth/otp/request', {
        method: 'POST',
        body: JSON.stringify({ phone: DEV_LOGIN_PHONE }),
      });
      if (!otpReq.debug_code) {
        sessionReady = null;
        throw new ApiError(500, 'dev 자동 로그인은 local 백엔드 환경(디버그 코드 노출)에서만 동작합니다');
      }
      const verify = await request<{ session_token: string }>('/api/v1/auth/otp/verify', {
        method: 'POST',
        body: JSON.stringify({ phone: DEV_LOGIN_PHONE, code: otpReq.debug_code }),
      });
      sessionToken = verify.session_token;
      await request('/api/v1/auth/pin', { method: 'POST', body: JSON.stringify({ pin: DEV_PIN }) });
    })().catch((err) => {
      sessionReady = null;
      throw err;
    });
  }
  return sessionReady;
}

interface ApiCaseListItem {
  id: string;
  case_code: string;
}

interface ApiApproval {
  id: string;
  status: string;
}

async function resolveApprovalId(caseCode: string): Promise<string> {
  const { cases } = await request<{ cases: ApiCaseListItem[] }>('/api/v1/cases');
  const match = cases.find((c) => c.case_code === caseCode);
  if (!match) throw new ApiError(404, `서버에 해당 케이스가 없습니다: ${caseCode}`);

  const params = new URLSearchParams({ case_id: match.id, status: 'pending' });
  const { approvals } = await request<{ approvals: ApiApproval[] }>(`/api/v1/approvals?${params}`);
  if (approvals.length === 0) throw new ApiError(404, `대기 중인 승인이 없습니다: ${caseCode}`);
  return approvals[0].id;
}

export interface DecideApprovalInput {
  caseCode: string;
  decision: 'approved' | 'rejected';
  idempotencyKey: string;
  reason?: string;
}

export async function decideApproval(input: DecideApprovalInput): Promise<void> {
  await ensureSession();
  const approvalId = await resolveApprovalId(input.caseCode);
  const path = `/api/v1/approvals/${approvalId}/${input.decision === 'approved' ? 'approve' : 'reject'}`;
  await request(path, {
    method: 'POST',
    body: JSON.stringify({
      idempotency_key: input.idempotencyKey,
      identity_method: 'pin',
      pin_code: DEV_PIN,
      // dev 대역(위 모듈 주석) — 저장된 checklist가 없으면 서버가 그냥 무시한다.
      checklist: [
        { key: 'target', checked: true },
        { key: 'docs', checked: true },
        { key: 'evidence', checked: true },
        { key: 'content', checked: true },
      ],
      reason: input.reason,
    }),
  });
}
