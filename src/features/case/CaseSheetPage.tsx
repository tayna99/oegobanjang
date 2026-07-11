import { useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { BriefingHomePage } from '@/features/briefing/BriefingHomePage';
import { CaseListPage } from '@/features/cases/CaseListPage';
import { CaseWorkbenchPage } from '@/features/cases/CaseWorkbenchPage';
import { useNav } from '@/lib/nav';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { CaseSheet } from './CaseSheet';

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

// 2단계 딥링크맵 §3 "case/{caseId} → M2 케이스 바텀시트". 목록에서 진입하면
// returnTo state를 사용해 M7 배경과 필터 컨텍스트를 보존하고, bare 링크는 M1 배경을 쓴다.
export function CaseSheetPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const nav = useNav();
  const isDesktop = useIsDesktop();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const routeState = location.state as CaseRouteState | null;
  const returnTo = safeCaseListReturnTo(routeState?.returnTo);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  // lg+ 에서는 바텀시트 대신 PC 워크벤치가 해당 케이스를 선택 상태로 렌더한다(M2.5.4).
  // returnTo에 실려 온 필터를 워크벤치 목록 레일에도 그대로 적용해 컨텍스트를 보존한다.
  if (isDesktop) {
    return <CaseWorkbenchPage selectedCaseId={caseId} filterOverride={filterFromReturnTo(returnTo)} />;
  }

  const card = caseId ? cases[caseId] : undefined;
  const sheet = caseId ? CASE_SHEETS[caseId] : undefined;

  return (
    <>
      {returnTo ? <CaseListPage filterOverride={filterFromReturnTo(returnTo)} /> : <BriefingHomePage />}
      {card && sheet && (
        <CaseSheet
          card={card}
          sheet={sheet}
          open
          onClose={() => (returnTo ? navigate(returnTo) : nav.toHome())}
        />
      )}
    </>
  );
}