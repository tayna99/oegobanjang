import { useEffect, useRef, useState } from 'react';
import { streamCommandRun } from './api/runs';
import type { RunAnswerFrame, RunApprovalFrame } from './api/runs';
import { useSessionStore } from '@/stores/sessionStore';
import type { RunStep } from '@/mocks/runs';

export type LiveRunEngineStatus = 'streaming' | 'done' | 'error';

export interface UseLiveRunEngineResult {
  steps: RunStep[];
  status: LiveRunEngineStatus;
  answer?: RunAnswerFrame;
  approval?: RunApprovalFrame;
  errorMessage?: string;
}

// useRunEngine(mock 픽스처 재생)의 실 데이터 버전 — CommandBar real 모드가 시작한 자연어
// 요청을 POST /api/v1/runs/stream(SSE)으로 실행하며 진행 상황을 노출한다(R4.1).
export function useLiveRunEngine(message: string): UseLiveRunEngineResult {
  const [steps, setSteps] = useState<RunStep[]>([]);
  const [status, setStatus] = useState<LiveRunEngineStatus>('streaming');
  const [answer, setAnswer] = useState<RunAnswerFrame | undefined>(undefined);
  const [approval, setApproval] = useState<RunApprovalFrame | undefined>(undefined);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);

  // 이 훅은 매번 실 백엔드 런(LLM 호출 포함)을 새로 시작시킨다. message 값 자체를 키로 써서,
  // React StrictMode의 개발 모드 이중 마운트(mount→cleanup→mount, 같은 message로 재호출)만
  // 막고 진짜 새 메시지(ref 값과 다름)는 정상적으로 새 런을 시작한다. 프로덕션 빌드는 애초에
  // 이중 마운트하지 않는다.
  const startedForMessageRef = useRef<string | null>(null);

  useEffect(() => {
    if (startedForMessageRef.current === message) return;
    startedForMessageRef.current = message;

    setSteps([]);
    setStatus('streaming');
    setAnswer(undefined);
    setApproval(undefined);
    setErrorMessage(undefined);

    const companyId = useSessionStore.getState().companyId;
    if (!companyId) {
      setStatus('error');
      setErrorMessage('로그인이 필요합니다.');
      return;
    }

    const controller = new AbortController();

    void (async () => {
      try {
        for await (const frame of streamCommandRun({ companyId, message }, controller.signal)) {
          if (frame.type === 'step') {
            const step: RunStep = { kind: frame.step.kind, label: frame.step.label, detail: frame.step.detail ?? '' };
            setSteps((prev) => [...prev, step]);
          } else if (frame.type === 'structured') {
            setAnswer(frame.data.answer ?? undefined);
            setApproval(frame.data.approval ?? undefined);
          } else if (frame.type === 'error') {
            setStatus('error');
            setErrorMessage(frame.detail);
          } else if (frame.type === 'done') {
            setStatus((prev) => (prev === 'error' ? prev : 'done'));
          }
        }
      } catch (err) {
        if (controller.signal.aborted) return; // 언마운트로 인한 취소는 에러로 표시하지 않는다
        setStatus('error');
        setErrorMessage(err instanceof Error ? err.message : '요청 처리 중 오류가 발생했습니다.');
      }
    })();

    return () => controller.abort();
  }, [message]);

  return { steps, status, answer, approval, errorMessage };
}
