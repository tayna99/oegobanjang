import { useEffect, useMemo } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { BriefingHomePage } from '@/features/briefing/BriefingHomePage';
import { CaseListPage } from '@/features/cases/CaseListPage';
import { useNav } from '@/lib/nav';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import type { CaseSheet as CaseSheetData } from '@/mocks/fixtures';
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
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);
  const docUpdates = useCaseStore((s) => (caseId ? s.docUpdates[caseId] : undefined));
  const routeState = location.state as CaseRouteState | null;
  const returnTo = safeCaseListReturnTo(routeState?.returnTo);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  const card = caseId ? cases[caseId] : undefined;
  const baseSheet = caseId ? CASE_SHEETS[caseId] : undefined;

  // 해석 확인(caseStore.applyInterpretationUpdates)이 남긴 docUpdates를 화면 표시용
  // statusLabel에 오버레이한다. CASE_SHEETS 원본과 CaseSheet 컴포넌트 계약은 건드리지 않는다.
  const sheet: CaseSheetData | undefined = useMemo(() => {
    if (!baseSheet) return undefined;
    if (!docUpdates || !baseSheet.docs) return baseSheet;
    return {
      ...baseSheet,
      docs: baseSheet.docs.map((doc) =>
        docUpdates[doc.name] ? { ...doc, statusLabel: docUpdates[doc.name].to } : doc,
      ),
    };
  }, [baseSheet, docUpdates]);

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