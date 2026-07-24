import { API_BASE_URL } from './config';

// R2.1 — 실서버 호출 공용 래퍼. 어댑터(api/auth.ts 등)만 이 함수를 쓰고, 스토어·화면은
// 어댑터가 반환하는 도메인 형태(camelCase)만 본다 — API 응답 스키마(snake_case)가 바뀌어도
// 어댑터 안에서만 고친다.
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

interface ApiFetchOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  token?: string;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (options.token) headers.Authorization = `Bearer ${options.token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorMessage(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// 코드리뷰 지적: FastAPI(backend/)는 모든 에러를 HTTPException 기본 핸들러가 감싼
// `{"detail": "..."}` JSON으로 응답한다 — 원문 텍스트를 그대로 메시지로 쓰면 사용자에게
// 깨진 JSON 문자열이 그대로 노출된다. detail 필드를 우선 추출하고, JSON이 아니거나
// detail이 없으면 원문 텍스트로 폴백한다(테스트가 이 순서를 검증).
export async function extractErrorMessage(response: Response): Promise<string> {
  const text = await response.text().catch(() => '');
  if (!text) return response.statusText;
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed && typeof parsed === 'object' && 'detail' in parsed && typeof parsed.detail === 'string') {
      return parsed.detail;
    }
  } catch {
    // JSON이 아닌 원문 텍스트 — 아래에서 그대로 반환.
  }
  return text;
}
