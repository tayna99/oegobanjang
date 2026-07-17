import { useSessionStore } from '@/stores/sessionStore';
import { API_BASE_URL } from './config';

// 백엔드 접속점 공용 fetch 래퍼(R2.1~2.2, NEXT_ROADMAP 2.1·2.2) — mock 스토어 액션과 같은
// 시그니처를 유지하도록 호출부(도메인별 lib/api/*.ts)가 이 위에서 얇게 감싼다. 세션 토큰이
// 있으면 자동으로 Bearer 헤더를 첨부한다(2.2) — 로그인 전(OTP 요청/검증 자체)에는 토큰이
// 없어 그냥 생략된다.
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(`API 요청 실패 (${status})`);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const token = useSessionStore.getState().token;
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  const text = await response.text();
  const data: unknown = text.length > 0 ? JSON.parse(text) : undefined;

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }
  return data as T;
}
