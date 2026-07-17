import { useSearchParams } from 'react-router-dom';
import { normalizeCaseFilter } from '@/lib/cases';
import { useSeedCases } from '@/lib/dataSeed';
import { useNav } from '@/lib/nav';
import { ROUTES } from '@/lib/routes';
import { useCaseStore } from '@/stores/caseStore';
import { CaseWorkbench } from './CaseWorkbench';

interface CaseWorkbenchPageProps {
  selectedCaseId?: string;
  filterOverride?: string | null;
}

// PC 워크벤치 컨테이너(M2.5.4) — /cases와 /case/:caseId 두 라우트가 lg+에서 공유한다.
// 행 클릭은 nav.toCase로 URL을 바꾸고(목록↔상세 동기), returnTo에 현재 필터를 실어
// 모바일 시트 흐름과 동일한 규약을 유지한다.
export function CaseWorkbenchPage({ selectedCaseId, filterOverride }: CaseWorkbenchPageProps) {
  const nav = useNav();
  const [searchParams] = useSearchParams();
  const cases = useCaseStore((state) => state.cases);

  useSeedCases();

  const preset = normalizeCaseFilter(filterOverride ?? searchParams.get('filter'));
  const returnTo = ROUTES.cases(preset === 'all' ? undefined : preset);

  return (
    <CaseWorkbench
      cards={Object.values(cases)}
      preset={preset}
      selectedCaseId={selectedCaseId}
      onSelectCase={(caseId) => nav.toCase(caseId, { state: { returnTo } })}
      onSelectFilter={nav.toCases}
      onOpenRun={(runRef) => nav.toRun(runRef)}
      onImport={() => nav.toCasesImport()}
      onOpenWorkerData={() => nav.toCasesWorkers()}
      onOpenDispatch={() => nav.toCasesDispatch()}
    />
  );
}
