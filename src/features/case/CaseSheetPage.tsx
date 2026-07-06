import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { BriefingHomePage } from '@/features/briefing/BriefingHomePage';
import { useNav } from '@/lib/nav';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { CaseSheet } from './CaseSheet';

// 2단계 딥링크맵 §3 "case/{caseId} → M2 케이스 바텀시트 (M1 위에 오버레이)" — createBrowserRouter
// 데이터 라우터에선 진짜 background-location 유지가 복잡해(공식 레시피는 <Routes> JSX API 기준),
// 실제 M1 렌더러(BriefingHomePage)를 배경으로 재사용하는 근사로 대체한다. M7(2.1)이 생기면
// "어디서 왔는지"를 봐서 배경을 M1/M7 중 고르도록 확장할 수 있다 — 지금은 항상 M1.
export function CaseSheetPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const card = caseId ? cases[caseId] : undefined;
  const sheet = caseId ? CASE_SHEETS[caseId] : undefined;

  return (
    <>
      <BriefingHomePage />
      {card && sheet && <CaseSheet card={card} sheet={sheet} open onClose={() => nav.toHome()} />}
    </>
  );
}
