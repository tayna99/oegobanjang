import { create } from 'zustand';
import type { RunStep } from '@/mocks/runs';
import { streamCommandRun } from '@/lib/api/runs';

// SD-4 — CommandBar→RunPage 핸드오프 저장소. `POST /runs/stream`은 조회 API가 없는
// "생성+실행 겸용" 엔드포인트라(plans/SEED_DESIGN_2026-07-20.md Part C SD-4 설계 문제)
// CommandBar가 스트림을 연 뒤 run_id가 도착하면 그 즉시 이 스토어에 항목을 만들고, RunPage는
// 그 항목을 구독만 한다(스트림을 다시 열지 않는다 — 두 번째 POST=중복 실행 부작용 방지).
// 컴포넌트 마운트/언마운트와 무관하게 스토어가 프레임을 계속 받는다 — RunPage를 나갔다
// 들어와도(또는 애초에 CommandBar가 아직 언마운트되지 않은 상태에서도) 지금까지 쌓인 상태를
// 그대로 이어 본다.
export interface LiveRunState {
  runId: string;
  /** 사용자가 커맨드 바에 입력한 원문 — mock RunConfig.title 자리에 대응(2.5.4b식 커맨드 제목 관례). */
  message: string;
  status: 'streaming' | 'done' | 'error';
  steps: RunStep[];
  /** structured 프레임의 answer.final_response — 사람이 읽는 결과 텍스트는 이 필드가 유일하다. */
  finalAnswer: string | null;
  approvalRequired: boolean;
  /** done 프레임의 run.status(backend runs.status CHECK 값) — UI가 직접 분기하진 않지만 감사용으로 보존. */
  runStatus: string | null;
  /** route.should_run === false(금지어·미인식 의도) — steps 없이 곧장 종료되는 경로. */
  blocked: boolean;
  blockedIntent: string | null;
  errorDetail: string | null;
}

interface LiveRunStoreState {
  runs: Record<string, LiveRunState>;
  /** CommandBar 전용 진입점 — run_created 프레임이 도착하면 그 run_id로 resolve한다(호출부가
   * 그 즉시 nav.toRun(runId)). 이후 프레임은 스토어 갱신으로만 반영되고 이 promise와 무관하다. */
  startCommandRun: (params: { companyId: string; message: string; threadId?: string }) => Promise<string>;
  reset: () => void;
}

export const useLiveRunStore = create<LiveRunStoreState>((set) => ({
  runs: {},

  startCommandRun: (params) =>
    new Promise<string>((resolve, reject) => {
      let runId: string | null = null;
      let settled = false; // run_created(성공) 또는 run_created 이전 onError(실패)로만 한 번 결정된다.

      const patchRun = (updates: Partial<LiveRunState>) => {
        const id = runId;
        if (!id) return;
        set((s) => (s.runs[id] ? { runs: { ...s.runs, [id]: { ...s.runs[id], ...updates } } } : s));
      };

      streamCommandRun(
        { companyId: params.companyId, message: params.message, threadId: params.threadId },
        {
          onRunCreated: (id) => {
            runId = id;
            settled = true;
            set((s) => ({
              runs: {
                ...s.runs,
                [id]: {
                  runId: id,
                  message: params.message,
                  status: 'streaming',
                  steps: [],
                  finalAnswer: null,
                  approvalRequired: false,
                  runStatus: null,
                  blocked: false,
                  blockedIntent: null,
                  errorDetail: null,
                },
              },
            }));
            resolve(id);
          },
          onRoute: (route) => {
            if (!route.should_run) patchRun({ blocked: true, blockedIntent: route.intent ?? null });
          },
          onStep: (step: RunStep) => {
            const id = runId;
            if (!id) return;
            set((s) => (s.runs[id] ? { runs: { ...s.runs, [id]: { ...s.runs[id], steps: [...s.runs[id].steps, step] } } } : s));
          },
          onStructured: (data) => {
            patchRun({ finalAnswer: data.answer.final_response, approvalRequired: data.approval.required });
          },
          onDone: (data) => {
            patchRun({ status: 'done', runStatus: data.status, approvalRequired: data.approval_required ?? false });
          },
          onError: (detail) => {
            if (!settled) {
              settled = true;
              reject(new Error(detail));
              return;
            }
            patchRun({ status: 'error', errorDetail: detail });
          },
        },
      );
    }),

  reset: () => set({ runs: {} }),
}));
