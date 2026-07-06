import { useParams } from 'react-router-dom';
import { useNav } from '@/lib/nav';
import { useRunEngine } from '@/lib/useRunEngine';
import { RUN_CONFIGS } from '@/mocks/runs';
import type { RunConfig } from '@/mocks/runs';
import { RunScreen } from './RunScreen';
import type { RunViewState } from './RunScreen';

// M4(/case/:caseId/approve)와 M9(/run/:runId) 둘 다 이 컨테이너를 마운트한다
// (ARCHITECTURE.md §5 "M4는 이 화면의 mode='approval' 사용처") — router.tsx가
// 어떤 파라미터로 진입했는지에 따라 조회 방식만 달라진다.
export function RunPage() {
  const { caseId, runId } = useParams<{ caseId?: string; runId?: string }>();

  const config = caseId
    ? RUN_CONFIGS.find((c) => c.caseId === caseId && c.mode === 'approval')
    : RUN_CONFIGS.find((c) => c.runKey === runId);

  if (!config) {
    return <RunScreen state={{ status: 'loading' }} />;
  }

  return <RunPageContent config={config} />;
}

function RunPageContent({ config }: { config: RunConfig }) {
  const nav = useNav();
  const engine = useRunEngine(config);

  // 승인 시 /done으로 이동만 한다 — approvalStore.decide() 등 상태 영속화는 1.6 몫.
  const state: RunViewState = {
    status: 'default',
    mode: config.mode,
    title: config.title,
    question: config.question,
    altLabel: config.altLabel,
    steps: engine.steps,
    engineStatus: engine.status,
    readOnly: config.readOnly,
  };

  return <RunScreen state={state} onApprove={() => nav.toDone()} onAlt={() => nav.toHome()} />;
}
