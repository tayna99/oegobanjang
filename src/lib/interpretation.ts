import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useThreadStore } from '@/stores/threadStore';

// M6 응답 해석 확인의 단일 출처 — ThreadPage(모바일)·MessagesWorkbench(PC)가 각자
// confirmInterpretation→applyInterpretationUpdates→evidence append 오케스트레이션을
// 거의 그대로 복제하고 있었다(코드리뷰 reuse 지적 — 특히 evidence id 규칙까지 같아서,
// 한쪽만 고치면 다른 쪽이 조용히 어긋나기 쉬웠다). lib/approval.ts의 useApprovalActions와
// 동일한 분리 원칙 — 화면은 이 훅만 부르고 코레오그래피를 인라인 재구현하지 않는다.
export function useConfirmInterpretation() {
  const confirmInterpretation = useThreadStore((s) => s.confirmInterpretation);
  const applyInterpretationUpdates = useCaseStore((s) => s.applyInterpretationUpdates);
  const appendEvidence = useEvidenceStore((s) => s.append);

  return (threadId: string) => {
    // 이중 클릭 방지: 호출 시점의 최신 스토어 상태를 다시 확인한다(버튼이 사라지는 것과
    // 별개로, 동일 틱 안의 재호출도 여기서 막는다).
    const current = useThreadStore.getState().threads[threadId];
    if (!current || current.interpretationStatus !== 'pending_review' || !current.interpretation) return;

    const updateIds = current.interpretation.updates.map((update) => update.updateId);
    const interpretation = confirmInterpretation(threadId, updateIds);
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
  };
}
