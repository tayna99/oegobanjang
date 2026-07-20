import { useSessionStore } from '@/stores/sessionStore';
import type { RunStep, RunStepKind } from '@/mocks/runs';
import { API_BASE_URL } from './config';

// SD-4 — POST /api/v1/runs/stream(SSE) 소비 어댑터. 이 엔드포인트는 POST+Authorization
// 헤더가 필요해 EventSource(GET 전용, 커스텀 헤더·바디 불가)를 쓸 수 없다
// (plans/SEED_DESIGN_2026-07-20.md Part C SD-4 배경, plans/BACKEND_CONNECT.md §3-2는
// "cancel=EventSource.close"를 전제했으나 이 제약으로 무효화됨) — fetch()+ReadableStream
// reader로 "event: <type>\ndata: <json>\n\n" 프레임을 직접 파싱한다
// (backend/app/api/v1/runs.py의 _sse() 와이어 포맷과 1:1 대응, LF 종료·빈 줄 구분).

export interface RunRouteDto {
  should_run: boolean;
  intent?: string | null;
  [key: string]: unknown;
}

// backend RagAnswer(rag/src/oe_rag/agent/factory.py) — final_response가 사용자에게 보여줄
// 한국어 답변 본문(사람이 읽는 텍스트는 이 필드뿐 — route/approval에는 자유 텍스트가 없다).
export interface RunAnswerDto {
  final_response: string;
  citations: unknown[];
  missing_evidence: boolean;
  risk_flags: string[];
}

export interface RunApprovalDto {
  required: boolean;
  status: string;
  blocked_actions: string[];
  reason: string;
}

export interface RunStructuredDto {
  answer: RunAnswerDto;
  approval: RunApprovalDto;
}

export interface RunDoneDto {
  run_id: string;
  status: string;
  // 차단된 라우팅(should_run=false) 경로의 done 프레임엔 이 필드 자체가 없다(run_service.py) —
  // 호출부가 approval_required ?? false로 다룬다.
  approval_required?: boolean;
}

export interface StreamCommandRunParams {
  companyId: string;
  message: string;
  threadId?: string;
}

export interface StreamCommandRunCallbacks {
  onRunCreated?: (runId: string) => void;
  onRoute?: (route: RunRouteDto) => void;
  onStep?: (step: RunStep) => void;
  onStructured?: (data: RunStructuredDto) => void;
  onDone?: (data: RunDoneDto) => void;
  onError?: (detail: string) => void;
}

export interface StreamCommandRunHandle {
  cancel: () => void;
}

const RUN_STEP_KINDS: readonly RunStepKind[] = ['thinking', 'tool_call', 'guardrail', 'handoff', 'replan'];

// backend가 db CHECK와 완전히 일치하는 kind만 보낸다고 문서화돼 있지만(BACKEND_CONNECT §B3'),
// 프론트 타입 안전을 위해 방어적으로 한 번 더 좁힌다 — 알 수 없는 값은 'thinking'으로 폴백.
function toRunStep(raw: unknown): RunStep {
  const step = (raw ?? {}) as { kind?: string; label?: string; detail?: string };
  const kind = RUN_STEP_KINDS.includes(step.kind as RunStepKind) ? (step.kind as RunStepKind) : 'thinking';
  return { kind, label: step.label ?? '', detail: step.detail ?? '' };
}

function dispatchFrame(rawFrame: string, callbacks: StreamCommandRunCallbacks): void {
  let eventType = 'message';
  let dataText = '';
  for (const line of rawFrame.split('\n')) {
    if (line.startsWith('event:')) eventType = line.slice(6).trim();
    else if (line.startsWith('data:')) dataText += line.slice(5).trim();
  }
  if (!dataText) return;

  let data: unknown;
  try {
    data = JSON.parse(dataText);
  } catch {
    return; // 손상된 프레임 — 다음 프레임에서 계속 이어갈 수 있으므로 조용히 건너뛴다.
  }

  switch (eventType) {
    case 'run_created':
      callbacks.onRunCreated?.((data as { run_id: string }).run_id);
      break;
    case 'route':
      callbacks.onRoute?.((data as { route: RunRouteDto }).route);
      break;
    case 'step':
      callbacks.onStep?.(toRunStep((data as { step: unknown }).step));
      break;
    case 'structured':
      callbacks.onStructured?.((data as { data: RunStructuredDto }).data);
      break;
    case 'done':
      callbacks.onDone?.(data as RunDoneDto);
      break;
    case 'error':
      callbacks.onError?.((data as { detail?: string }).detail ?? '알 수 없는 오류');
      break;
    default:
      // evidence 프레임 등 — 서버가 이미 자기 트랜잭션 안에서 영속화했으므로(run_service.py)
      // 프론트가 소비하지 않아도 안전하다. 후속에서 필요해지면 여기 case만 추가하면 된다.
      break;
  }
}

// POST /api/v1/runs/stream을 열고(1회) SSE 프레임을 콜백으로 중계한다. 이 함수를 호출하는
// 쪽이 곧 "런을 실행하는" 쪽이다 — 같은 런에 대해 두 번 호출하면 서버에 두 번째 실행(중복
// 부작용)이 생기므로, 호출부(liveRunStore)가 CommandBar에서 딱 한 번만 부르고 RunPage는
// 그 결과를 구독만 하도록 설계됐다(plans/SEED_DESIGN_2026-07-20.md Part C SD-4 핸드오프 설계).
export function streamCommandRun(
  params: StreamCommandRunParams,
  callbacks: StreamCommandRunCallbacks,
): StreamCommandRunHandle {
  const controller = new AbortController();
  const token = useSessionStore.getState().token ?? undefined;

  void consume();

  async function consume(): Promise<void> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/runs/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          company_id: params.companyId,
          message: params.message,
          thread_id: params.threadId ?? null,
        }),
        signal: controller.signal,
      });
    } catch (err) {
      if (controller.signal.aborted) return;
      callbacks.onError?.(err instanceof Error ? err.message : 'SSE 연결 실패');
      return;
    }

    if (!response.ok || !response.body) {
      callbacks.onError?.(`요청 실패 (${response.status})`);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    try {
      for (;;) {
        if (controller.signal.aborted) break;
        const { done, value } = await reader.read();
        if (controller.signal.aborted) break;
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let frameEnd = buffer.indexOf('\n\n');
        while (frameEnd !== -1) {
          if (controller.signal.aborted) return;
          const frame = buffer.slice(0, frameEnd);
          buffer = buffer.slice(frameEnd + 2);
          if (frame.trim()) dispatchFrame(frame, callbacks);
          frameEnd = buffer.indexOf('\n\n');
        }
      }
    } catch (err) {
      if (controller.signal.aborted) return; // cancel() 호출로 인한 중단 — 에러로 보고하지 않는다.
      callbacks.onError?.(err instanceof Error ? err.message : 'SSE 스트림 읽기 실패');
    }
  }

  return { cancel: () => controller.abort() };
}
