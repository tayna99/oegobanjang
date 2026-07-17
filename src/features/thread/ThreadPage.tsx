import { Navigate, useParams } from 'react-router-dom';
import { Button } from '@/components/Button';
import { useSeedThreadDetail, useSeedThreads } from '@/lib/dataSeed';
import { useNav } from '@/lib/nav';
import { ROUTES } from '@/lib/routes';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useThreadStore } from '@/stores/threadStore';
import type { MessageThread } from '@/types';
import { ThreadScreen } from './ThreadScreen';
import type { ThreadViewState } from './ThreadScreen';

// 컨테이너 — 스토어 시딩·조회 + onConfirm 오케스트레이션만. 화면 렌더는 ThreadScreen(프레젠테이션)
// 몫(CaseListPage.tsx/MessagesPage.tsx와 동일한 컨테이너/프레젠테이션 분리 패턴).
// 탭별기획 §3.3 3분기: (1) 승인 대기 초안 → M3 직행 (2) 응답 도착 → M6 (3) 완료 → 타임라인.
export function ThreadPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const nav = useNav();
  const threads = useThreadStore((s) => s.threads);
  const confirmInterpretation = useThreadStore((s) => s.confirmInterpretation);
  const applyInterpretationUpdates = useCaseStore((s) => s.applyInterpretationUpdates);
  const appendEvidence = useEvidenceStore((s) => s.append);

  useSeedThreads();
  useSeedThreadDetail(threadId);

  const thread = threadId ? threads[threadId] : undefined;

  if (!thread) {
    return (
      <div className="p-5">
        <p className="text-sm text-muted">스레드를 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toMessages()}>
          메시지 탭으로
        </Button>
      </div>
    );
  }

  // 승인 대기 초안(아직 미발송)은 스레드 뷰를 거치지 않고 M3로 직행 — 리스트 탭(MessagesPage)
  // 진입 규칙과 라우트 직접 진입(딥링크) 규칙을 일관되게 유지한다(탭별기획 §3.3).
  if (thread.draftCaseId && thread.messages.length === 0) {
    return <Navigate replace to={ROUTES.caseDraft(thread.draftCaseId)} />;
  }

  // 위 가드 이후로는 항상 정의된 스레드 — 별도 바인딩으로 고정해 아래 클로저(handleConfirm 등)에서
  // 매번 undefined 가능성을 따지지 않게 한다(TS는 중첩 함수로는 좁힌 타입을 들고 가지 않는다).
  const activeThread: MessageThread = thread;

  function handleConfirm(updateIds: string[]) {
    // 이중 클릭 방지: 현재 스토어 상태를 다시 확인해 pending_review가 아니면 아무것도 하지 않는다
    // (버튼이 timeline 모드 전환으로 사라지는 것과 별개로, 동일 틱 안의 재호출도 여기서 막는다).
    const current = useThreadStore.getState().threads[activeThread.threadId];
    if (!current || current.interpretationStatus !== 'pending_review') return;

    const interpretation = confirmInterpretation(activeThread.threadId, updateIds);
    applyInterpretationUpdates(interpretation.caseId, interpretation.updates);
    appendEvidence({
      id: `${interpretation.interpretationId}-confirmed`,
      type: 'interpretation_confirmed',
      at: new Date().toISOString(),
      caseId: interpretation.caseId,
      evidenceRef: interpretation.evidenceRef,
      // 근로자 원문을 절대 포함하지 않는 요약 문장만 — confirmedSummary가 Evidence summary와
      // 동일해야 한다는 계약(types.ts 주석)을 그대로 따른다.
      summary: interpretation.confirmedSummary ?? interpretation.summaryKo,
    });
  }

  let state: ThreadViewState;
  if (activeThread.interpretationStatus === 'pending_review' && activeThread.interpretation) {
    state = {
      status: 'default',
      mode: 'interpretation',
      thread: activeThread,
      interpretation: activeThread.interpretation,
    };
  } else if (activeThread.messages.length === 0) {
    state = { status: 'empty', thread: activeThread };
  } else {
    state = { status: 'default', mode: 'timeline', thread: activeThread };
  }

  return (
    <ThreadScreen
      state={state}
      onConfirm={handleConfirm}
      onNewDraft={() => activeThread.caseId && nav.toDraft(activeThread.caseId)}
    />
  );
}
