import { useSessionStore } from '@/stores/sessionStore';
import type { RunStepKind } from '@/mocks/runs';
import { API_BASE_URL } from './config';
import { ApiError, extractErrorMessage } from './client';

// POST /api/v1/runs/stream 어댑터(R4.1) — backend/app/api/v1/runs.py의 `_sse()`가 만드는
// "event: <type>\ndata: <json>\n\n" 프레임을 그대로 소비한다. apiFetch(client.ts)는 JSON 응답
// 전용이라 재사용 불가 — 이 파일만 raw fetch + ReadableStream 리더를 쓴다.

export interface RunStepFrame {
  kind: RunStepKind;
  label: string;
  detail?: string | null;
}

export interface RunCitationFrame {
  source_id: string;
  title: string;
  evidence_grade: string;
}

export interface RunAnswerFrame {
  final_response: string;
  citations: RunCitationFrame[];
  missing_evidence: boolean;
  risk_flags: string[];
}

export interface RunApprovalFrame {
  required: boolean;
  status: string;
  blocked_actions: string[];
  reason: string;
}

export type RunSseFrame =
  | { type: 'run_created'; run_id: string }
  | { type: 'route'; route: unknown }
  | { type: 'step'; step: RunStepFrame }
  | { type: 'evidence'; event: unknown }
  | { type: 'structured'; data: { answer: RunAnswerFrame | null; approval: RunApprovalFrame | null } }
  | { type: 'error'; detail: string }
  | { type: 'done'; run_id: string; status: string; approval_required?: boolean };

export async function* streamCommandRun(
  params: { companyId: string; message: string },
  signal?: AbortSignal,
): AsyncGenerator<RunSseFrame> {
  const token = useSessionStore.getState().token ?? undefined;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}/api/v1/runs/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ company_id: params.companyId, message: params.message }),
    signal,
  });

  // 403(멤버십 없음)·422(빈 message 등)는 text/event-stream이 아니라 일반 JSON
  // {"detail": "..."}로 온다 — SSE 파서에 그대로 흘려보내면 조용히 빈 스트림으로 끝난다.
  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorMessage(response));
  }
  if (!response.body) {
    throw new ApiError(response.status, '스트림 응답 본문이 없습니다');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      while (true) {
        const separatorIndex = buffer.indexOf('\n\n');
        if (separatorIndex === -1) break;
        const rawFrame = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);
        const frame = parseSseFrame(rawFrame);
        if (frame) yield frame;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseSseFrame(raw: string): RunSseFrame | null {
  let eventType = '';
  let dataLine = '';
  for (const line of raw.split('\n')) {
    if (line.startsWith('event: ')) eventType = line.slice('event: '.length);
    else if (line.startsWith('data: ')) dataLine = line.slice('data: '.length);
  }
  if (!eventType || !dataLine) return null;
  const data = JSON.parse(dataLine) as Record<string, unknown>;
  return { type: eventType, ...data } as RunSseFrame;
}
