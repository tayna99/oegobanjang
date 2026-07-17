import { useEffect } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { buildCaseGroups, normalizeCaseFilter } from '@/lib/cases';
import { useNav } from '@/lib/nav';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { CaseListScreen } from './CaseListScreen';
import { CaseWorkbenchPage } from './CaseWorkbenchPage';

interface CaseListPageProps {
  filterOverride?: string | null;
}

export function CaseListPage({ filterOverride }: CaseListPageProps = {}) {
  const nav = useNav();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const isDesktop = useIsDesktop();
  const cases = useCaseStore((state) => state.cases);
  const upsert = useCaseStore((state) => state.upsert);
  const companyName = useCompanyStore((s) => s.profile.name);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  // lg+ 에서는 M2.5.4 PC 워크벤치(3열)로 분기 — 모바일 트리는 마운트하지 않는다.
  if (isDesktop) {
    return <CaseWorkbenchPage filterOverride={filterOverride} />;
  }

  const preset = normalizeCaseFilter(filterOverride ?? searchParams.get('filter'));
  const cards = Object.values(cases);
  const groups = buildCaseGroups(cards, preset);
  const returnTo = `${location.pathname}${location.search}`;

  return (
    <CaseListScreen
      companyName={companyName}
      totalCount={cards.length}
      preset={preset}
      groups={groups}
      onSelectFilter={nav.toCases}
      onClearFilter={() => nav.toCases()}
      onOpenCase={(caseId) => nav.toCase(caseId, { state: { returnTo } })}
    />
  );
}