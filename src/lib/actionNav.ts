import { useNav } from '@/lib/nav';
import { threadFor } from '@/mocks/messages';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { NextActionRef } from '@/types';

// CTA의 kind → 실제 동작(이동 또는 인라인 액션) 매핑. M1이 처음 쓰지만
// 케이스 시트(M2) 등 NextActionRef를 렌더하는 모든 화면이 재사용한다.
export function useNextAction() {
  const nav = useNav();
  const append = useEvidenceStore((s) => s.append);

  return (caseId: string, action: NextActionRef) => {
    switch (action.kind) {
      case 'approve':
        nav.toApprove(caseId);
        return;
      case 'draft':
        nav.toDraft(caseId);
        return;
      case 'detail':
        nav.toCase(caseId);
        return;
      case 'thread': {
        // M1/M2의 [응답 요약 보기]는 메시지 탭이 아니라 해당 스레드(M6)로 바로 이동한다
        // (탭별기획 "M1 [응답 요약 보기] → M6"). MESSAGE_THREADS는 threadId=caseId로 1:1
        // 대응한다(mocks/messages.ts) — 매핑이 없으면(아직 스레드가 없는 케이스 등) 메시지 탭 폴백.
        if (threadFor(caseId)) {
          nav.toThread(caseId);
        } else {
          nav.toMessages();
        }
        return;
      }
      case 'package':
        nav.toPackage(caseId);
        return;
      case 'confirm':
        // v3 confirmTranCase() 동등 — 이동 없이 판단 기록만 남긴다(케이스
        // 상태 전이는 하지 않는다: risk_review → completed는 CASE_TRANSITIONS에
        // 없는 경로라 caseStore.transition()을 부르면 GuardrailError가 난다).
        append({
          id: `${action.actionId}-${caseId}-confirm`,
          type: 'approval_decided',
          at: new Date().toISOString(),
          caseId,
          actionId: action.actionId,
        });
        return;
    }
  };
}
