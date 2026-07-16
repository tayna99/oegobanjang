import { useLocation, useParams } from 'react-router-dom';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { CaseWorkbenchPage } from '@/features/cases/CaseWorkbenchPage';
import { CaseReviewPage } from './CaseReviewPage';

interface CaseRouteState {
  returnTo?: string;
}

function safeCaseListReturnTo(value: unknown): string | undefined {
  return typeof value === 'string' && (value === '/cases' || value.startsWith('/cases?')) ? value : undefined;
}

function filterFromReturnTo(returnTo: string | undefined): string | null {
  if (!returnTo) return null;
  const query = returnTo.split('?')[1];
  return query ? new URLSearchParams(query).get('filter') : null;
}

// /case/:caseId 컨테이너 — M2.6.2에서 모바일 바텀시트(M2)를 2b 전면 검토 페이지로 교체
// (블루프린트 §1: "카드에서는 검토만, 승인은 체크리스트 화면에서").
// 데스크톱은 2.5.4 워크벤치가 해당 케이스를 선택 상태로 렌더한다. 딥링크 경로 계약(2단계 §3) 불변.
export function CaseSheetPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const location = useLocation();
  const isDesktop = useIsDesktop();
  const returnTo = safeCaseListReturnTo((location.state as CaseRouteState | null)?.returnTo);

  if (isDesktop) {
    return <CaseWorkbenchPage selectedCaseId={caseId} filterOverride={filterFromReturnTo(returnTo)} />;
  }
  return <CaseReviewPage />;
}
