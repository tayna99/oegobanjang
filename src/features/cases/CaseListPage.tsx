import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { buildCaseGroups, normalizeCaseFilter } from '@/lib/cases';
import { useNav } from '@/lib/nav';
import { CaseListScreen } from './CaseListScreen';

const COMPANY_NAME = '화성 1공장';

export function CaseListPage() {
  const nav = useNav();
  const [searchParams] = useSearchParams();
  const cases = useCaseStore((state) => state.cases);
  const upsert = useCaseStore((state) => state.upsert);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const preset = normalizeCaseFilter(searchParams.get('filter'));
  const cards = Object.values(cases);
  const groups = buildCaseGroups(cards, preset);

  return (
    <CaseListScreen
      companyName={COMPANY_NAME}
      totalCount={cards.length}
      preset={preset}
      groups={groups}
      onSelectFilter={nav.toCases}
      onClearFilter={() => nav.toCases()}
      onOpenCase={nav.toCase}
    />
  );
}