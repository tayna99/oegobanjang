import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLiveRunEngine } from '@/lib/useLiveRunEngine';
import type { RunAnswerView, RunViewState } from './RunScreen';
import { RunScreen } from './RunScreen';

interface LiveRunLocationState {
  message?: string;
}

const NOT_FOUND_MESSAGE = '진행 중인 요청 정보를 찾을 수 없습니다. 검색창에서 다시 요청해 주세요.';

// R4.1 — CommandBar real 모드의 착지 화면(/run/live). RunPage(mock RUN_CONFIGS 재생)와 완전히
// 분리된 별도 파일이다 — 광범위하게 테스트된 mock 데모 경로(RunPage/RUN_CONFIGS)를 건드리지
// 않기 위해서다.
export function RunLivePage() {
  const location = useLocation();
  const navigate = useNavigate();

  // 최초 렌더에서만 message를 읽어 고정한다(lazy initializer, 이후 location 변화에 반응하지
  // 않음) — 아래 effect가 마운트 직후 history state를 지우는데, location.state를 매 렌더
  // 다시 읽으면 지워진 직후 렌더에서 message가 사라져 버린다.
  const [message] = useState<string | undefined>(
    () => (location.state as LiveRunLocationState | null)?.message,
  );

  // 새로고침·뒤로가기 재진입 시 남아있는 message로 실 백엔드 런(LLM 호출 포함)이 재실행되지
  // 않도록, 읽은 직후 state를 즉시 소거한다(Plan 검증에서 발견한 리스크 대응).
  useEffect(() => {
    if (message) {
      navigate(location.pathname, { replace: true, state: null });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!message) {
    return <RunScreen state={{ status: 'error', reason: 'unknown', message: NOT_FOUND_MESSAGE }} />;
  }

  return <RunLiveContent message={message} />;
}

function RunLiveContent({ message }: { message: string }) {
  const engine = useLiveRunEngine(message);

  if (engine.status === 'error') {
    return (
      <RunScreen
        state={{ status: 'error', reason: 'unknown', message: engine.errorMessage ?? '요청을 처리하지 못했습니다.' }}
      />
    );
  }

  const answer: RunAnswerView | undefined = engine.answer
    ? {
        text: engine.answer.final_response,
        citations: engine.answer.citations.map((c) => ({
          sourceId: c.source_id,
          title: c.title,
          grade: c.evidence_grade,
        })),
        missingEvidence: engine.answer.missing_evidence,
        // 액션 버튼은 만들지 않는다 — 승인할 케이스·초안이 없는 순수 QA(범위: Tier1).
        // 침묵하지 않고 정보로만 알린다(AGENTS.md §8).
        approvalNotice: engine.approval?.required
          ? engine.approval.reason || '이 요청은 담당자 검토가 필요합니다.'
          : undefined,
      }
    : undefined;

  const state: RunViewState = {
    status: 'default',
    mode: 'command',
    title: message,
    question: '',
    altLabel: '',
    steps: engine.steps,
    engineStatus: engine.status === 'done' ? 'done' : 'streaming',
    readOnly: true,
    answer,
  };

  return <RunScreen state={state} />;
}
