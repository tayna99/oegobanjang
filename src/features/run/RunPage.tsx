import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useNav } from '@/lib/nav';
import { canTransition, useCaseStore } from '@/stores/caseStore';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRunEngine } from '@/lib/useRunEngine';
import { CASE_CARDS } from '@/mocks/fixtures';
import { RUN_CONFIGS } from '@/mocks/runs';
import type { RunConfig } from '@/mocks/runs';
import { RunScreen } from './RunScreen';
import type { RunViewState } from './RunScreen';

// M4(/case/:caseId/approve)와 M9(/run/:runId)는 같은 컨테이너를 마운트한다.
// caseId 진입은 승인 런을, runId 진입은 재생/명령 런을 조회한다.
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
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const transition = useCaseStore((s) => s.transition);
  const approvals = useApprovalStore((s) => s.approvals);
  const requestApproval = useApprovalStore((s) => s.requestApproval);
  const decide = useApprovalStore((s) => s.decide);
  const appendEvidence = useEvidenceStore((s) => s.append);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const card = config.caseId ? cases[config.caseId] : undefined;

  const approve = () => {
    if (!card || !config.caseId) {
      nav.toDone({ state: { evidenceRef: config.evidenceRef } });
      return;
    }

    const actionId = card.primaryAction.actionId;
    if (!approvals[actionId]) requestApproval(actionId);

    const key = `${actionId}:${config.evidenceRef}:approved`;
    decide(actionId, 'approved', key);

    if (canTransition(card.state, 'human_approved')) {
      transition(config.caseId, 'human_approved');
    }

    appendEvidence({
      id: `${actionId}-approved`,
      type: 'approval_decided',
      at: new Date().toISOString(),
      caseId: config.caseId,
      actionId,
      evidenceRef: config.evidenceRef,
      summary: '사람 승인 결정 저장',
      actor: '담당자',
    });

    nav.toDone({ state: { caseTitle: card.title, evidenceRef: config.evidenceRef } });
  };

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

  return <RunScreen state={state} onApprove={approve} onAlt={() => nav.toHome()} />;
}
