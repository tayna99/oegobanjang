import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useNav } from '@/lib/nav';
import { useCaseStore } from '@/stores/caseStore';
import { useRoleStore } from '@/stores/roleStore';
import { useRunEngine } from '@/lib/useRunEngine';
import { CASE_CARDS } from '@/mocks/fixtures';
import { RUN_CONFIGS } from '@/mocks/runs';
import type { RunConfig } from '@/mocks/runs';
import { RunScreen } from './RunScreen';
import type { RunResultCase, RunViewState } from './RunScreen';

// M9(/run/:runId) 컨테이너 — 재생(replay)·명령(command)·승인(approval) 런을 runKey로 조회한다.
// 케이스 승인 "결정" 자체는 여기서 절대 내리지 않는다 — PIN·citation-lock·체크리스트 게이트를
// 모두 갖춘 ApprovePage(lib/approval.ts의 useApprovalActions 단일 출처)로만 넘긴다
// (코드리뷰 CRITICAL 교정: 이 파일이 이전에 decide/transition/evidence를 직접 호출해
// 게이트를 전부 우회하는 두 번째 승인 실행 경로였다).
export function RunPage() {
  const { runId } = useParams<{ runId: string }>();
  const config = RUN_CONFIGS.find((c) => c.runKey === runId);

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
  const role = useRoleStore((s) => s.role);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  // 3.2: 커맨드 런 결과 카드 대상 — 스토어 우선, 미시드 시 픽스처 폴백(제목·D-day 표시용).
  const resultCases: RunResultCase[] = (config.resultCaseIds ?? []).flatMap((id) => {
    const c = cases[id] ?? CASE_CARDS.find((x) => x.caseId === id);
    return c ? [{ caseId: id, title: c.title, dDay: c.dDay }] : [];
  });

  const approve = () => {
    // 케이스에 연결된 승인 모드 런은 결정을 내리지 않고 게이트가 있는 화면으로 넘긴다.
    if (config.caseId) {
      nav.toApprove(config.caseId);
      return;
    }
    // 케이스에 연결되지 않은 런(예: candidate 패키지 준비)은 결정할 케이스 상태가 없다.
    nav.toDone({ state: { evidenceRef: config.evidenceRef } });
  };

  // 4.2 라우트 가드 — owner의 M9는 읽기성 요청만(7단계 §2 각주3). 케이스/초안 등
  // 쓰기 도구를 쓰는 command 런은 owner 앞에서 실행하지 않고 차단 사유를 보여준다.
  const roleBlocked = role === 'owner' && config.mode === 'command' && config.writesData === true;

  const state: RunViewState = roleBlocked
    ? {
        status: 'error',
        reason: 'blocked',
        message: '이 요청은 담당자 권한이 필요합니다 — 대표 계정에서는 조회·요약 요청만 실행할 수 있습니다.',
      }
    : {
        status: 'default',
        mode: config.mode,
        title: config.title,
        question: config.question,
        altLabel: config.altLabel,
        steps: engine.steps,
        engineStatus: engine.status,
        readOnly: config.readOnly,
        resultCases,
      };

  return (
    <RunScreen
      state={state}
      onApprove={approve}
      onAlt={() => nav.toHome()}
      onOpenCase={(caseId) => nav.toCase(caseId)}
    />
  );
}
