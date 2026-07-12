import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Shell } from '@/Shell';
import { HomePage } from '@/features/HomePage';
import { CaseListPage } from '@/features/cases/CaseListPage';
import { CaseSheetPage } from '@/features/case/CaseSheetPage';
import { CaseHistoryPage } from '@/features/case/CaseHistoryPage';
import { ApprovePage } from '@/features/approve/ApprovePage';
import { RunPage } from '@/features/run/RunPage';
import { DraftPage } from '@/features/draft/DraftPage';
import { DonePage } from '@/features/done/DonePage';
import { EvidencePage } from '@/features/governance/EvidencePage';
import { PackagePage } from '@/features/packagePkg/PackagePage';
import { PlaceholderScreen } from '@/screens/PlaceholderScreen';
import { ROUTE_PATHS } from '@/lib/routes';
import { validateIdParam } from '@/lib/deeplink';

// 라우트 ↔ 스펙 매핑: docs/ARCHITECTURE.md §3.
// 딥링크 경로: reference/specs/2단계_알림카탈로그_딥링크맵_v1.md §3과 1:1.
export const routeConfig: RouteObject[] = [
  {
    element: <Shell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: ROUTE_PATHS.cases, element: <CaseListPage /> },
      {
        path: ROUTE_PATHS.case,
        loader: validateIdParam('caseId'),
        element: <CaseSheetPage />,
      },
      {
        path: ROUTE_PATHS.caseDraft,
        loader: validateIdParam('caseId'),
        element: <DraftPage />,
      },
      {
        // M2.6.3: 승인은 사람 체크리스트 페이지(2c)가 담당 — 에이전트 런은 /run/:runId로 이동.
        path: ROUTE_PATHS.caseApprove,
        loader: validateIdParam('caseId'),
        element: <ApprovePage />,
      },
      {
        path: ROUTE_PATHS.caseHistory,
        loader: validateIdParam('caseId'),
        element: <CaseHistoryPage />,
      },
      {
        path: ROUTE_PATHS.run,
        loader: validateIdParam('runId'),
        element: <RunPage />,
      },
      { path: ROUTE_PATHS.messages, element: <PlaceholderScreen name="메시지" /> },
      {
        path: ROUTE_PATHS.thread,
        loader: validateIdParam('threadId'),
        element: <PlaceholderScreen name="M6 응답 해석" />,
      },
      { path: ROUTE_PATHS.evidence, element: <EvidencePage /> },
      {
        path: ROUTE_PATHS.package,
        loader: validateIdParam('packageId'),
        element: <PackagePage />,
      },
      { path: ROUTE_PATHS.done, element: <DonePage /> },
      {
        path: ROUTE_PATHS.onboardingWorkers,
        element: <PlaceholderScreen name="근로자 등록" />,
      },
    ],
  },
];

export const router = createBrowserRouter(routeConfig);
