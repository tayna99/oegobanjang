import { useParams } from 'react-router-dom';
import { API_MODE } from '@/lib/api/config';
import { useSeedCases } from '@/lib/dataSeed';
import { useNav } from '@/lib/nav';
import { useLiveRunEngine } from '@/lib/useLiveRunEngine';
import { useCaseStore } from '@/stores/caseStore';
import { useLiveRunStore } from '@/stores/liveRunStore';
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
//
// SD-4 — RUN_CONFIGS에 없는 runId는 mock 모드에선 지금처럼 영원히 loading이지만, real
// 모드에서는 CommandBar가 POST /runs/stream을 시작하며 liveRunStore에 심어 둔 실시간 런일 수
// 있다(핸드오프 설계는 stores/liveRunStore.ts 참조 — RunPage는 그 스트림을 다시 열지 않고
// 구독만 한다). mock config 분기는 한 글자도 바뀌지 않는다.
export function RunPage() {
  const { runId } = useParams<{ runId: string }>();
  const config = RUN_CONFIGS.find((c) => c.runKey === runId);

  if (config) {
    return <RunPageContent config={config} />;
  }

  if (API_MODE === 'real' && runId) {
    return <LiveRunPageContent runId={runId} />;
  }

  return <RunScreen state={{ status: 'loading' }} />;
}

function RunPageContent({ config }: { config: RunConfig }) {
  const nav = useNav();
  const engine = useRunEngine(config);
  const cases = useCaseStore((s) => s.cases);
  const role = useRoleStore((s) => s.role);

  useSeedCases();

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

// SD-4 — CommandBar가 real 모드에서 이미 열어 둔 실시간 커맨드 런(POST /runs/stream)을
// liveRunStore에서 구독만 한다(두 번째 POST 없음, 위 모듈 주석 참조). 이 런은 아직 case를
// 만들지 않으므로(run_service.py — case 생성은 Daily Briefing Rule 엔진 몫, 후속) caseId가
// 항상 없다 — approve()는 mock의 "caseId 없는 커맨드 런"(candidate 등)과 동일하게 어떤
// 결정도 서버에 내리지 않고 DonePage로만 넘긴다(직접 발송 없음, 가드레일 준수).
function LiveRunPageContent({ runId }: { runId: string }) {
  const nav = useNav();
  const run = useLiveRunStore((s) => s.runs[runId]);
  const engine = useLiveRunEngine(runId);

  if (!run) {
    // 스토어에 없는 runId — 새로고침으로 스토어가 비었거나, 커맨드 바를 거치지 않고 직접
    // 진입한 경우. "생성+실행 겸용" 엔드포인트라 여기서 대신 새로 시작할 수 없으므로(중복
    // 실행) 영원한 loading 대신 재요청을 안내한다.
    return (
      <RunScreen
        state={{
          status: 'error',
          reason: 'unknown',
          message: '이 런을 찾을 수 없습니다 — 커맨드 바에서 새로 요청해주세요.',
        }}
      />
    );
  }

  if (run.blocked) {
    return (
      <RunScreen
        state={{
          status: 'error',
          reason: run.blockedIntent === 'forbidden' ? 'blocked' : 'unknown',
          message:
            run.blockedIntent === 'forbidden'
              ? '이 요청은 지원 범위 밖입니다 — 담당자 검토가 필요합니다.'
              : '요청을 이해하지 못했습니다 — 다른 방식으로 다시 시도해주세요.',
        }}
      />
    );
  }

  if (run.status === 'error') {
    return (
      <RunScreen
        state={{ status: 'error', reason: 'unknown', message: run.errorDetail ?? '요청을 처리하지 못했습니다.' }}
      />
    );
  }

  const state: RunViewState = {
    status: 'default',
    mode: 'command',
    title: run.message,
    question: run.finalAnswer ?? '',
    altLabel: '닫기',
    steps: engine.steps,
    engineStatus: engine.status,
  };

  return (
    <RunScreen
      state={state}
      onApprove={() => nav.toDone({ state: { evidenceRef: run.runId } })}
      onAlt={() => nav.toHome()}
      onOpenCase={(caseId) => nav.toCase(caseId)}
    />
  );
}
