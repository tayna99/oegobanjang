import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Shell } from '@/Shell';
import { HomePage } from '@/features/HomePage';
import { CaseListPage } from '@/features/cases/CaseListPage';
import { CsvUploadPage } from '@/features/cases/CsvUploadPage';
import { CaseSheetPage } from '@/features/case/CaseSheetPage';
import { CaseHistoryPage } from '@/features/case/CaseHistoryPage';
import { ApprovePage } from '@/features/approve/ApprovePage';
import { RunPage } from '@/features/run/RunPage';
import { DraftPage } from '@/features/draft/DraftPage';
import { DonePage } from '@/features/done/DonePage';
import { EvidencePage } from '@/features/governance/EvidencePage';
import { MessagesPage } from '@/features/messages/MessagesPage';
import { ThreadPage } from '@/features/messages/ThreadPage';
import { PackagePage } from '@/features/packagePkg/PackagePage';
import { ExpertLinkPage } from '@/features/packagePkg/ExpertLinkPage';
import { SettingsHubPage } from '@/features/settings/SettingsHubPage';
import { MembersPage } from '@/features/settings/MembersPage';
import { DelegationPage } from '@/features/settings/DelegationPage';
import { OnboardingFlow } from '@/features/onboarding/OnboardingFlow';
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
      // CSV 일괄 등록(4.4) — PC 전용(4b), case/:caseId보다 앞에 둘 필요는 없다(다른 최상위 세그먼트).
      { path: ROUTE_PATHS.casesImport, element: <CsvUploadPage /> },
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
      { path: ROUTE_PATHS.messages, element: <MessagesPage /> },
      {
        path: ROUTE_PATHS.thread,
        loader: validateIdParam('threadId'),
        element: <ThreadPage />,
      },
      { path: ROUTE_PATHS.evidence, element: <EvidencePage /> },
      {
        path: ROUTE_PATHS.package,
        loader: validateIdParam('packageId'),
        element: <PackagePage />,
      },
      { path: ROUTE_PATHS.done, element: <DonePage /> },
      { path: ROUTE_PATHS.settings, element: <SettingsHubPage /> },
      { path: ROUTE_PATHS.settingsMembers, element: <MembersPage /> },
      { path: ROUTE_PATHS.settingsDelegation, element: <DelegationPage /> },
    ],
  },
  // Shell(로그인 앱 챙) 바깥의 최상위 형제 라우트 — 행정사는 계정이 없어 nav/tabbar가 없다
  // (7단계 §1·§4). loader 없음 — 만료 여부는 화면 안에서 판정(리다이렉트가 아니라 안내문 표시).
  {
    path: ROUTE_PATHS.packageLinkAbsolute,
    element: <ExpertLinkPage />,
  },
  // 온보딩(4.1)도 로그인 전 전체 화면 플로우라 Shell 바깥 형제 라우트 — 상태 머신은
  // OnboardingFlow 내부에서 관리하고 딥링크 카탈로그(2단계)엔 O1~O5 개별 경로가 없다
  // (순차 게이트라 중간 단계 딥링크를 허용하지 않는다).
  {
    path: ROUTE_PATHS.onboardingAbsolute,
    element: <OnboardingFlow />,
  },
];

export const router = createBrowserRouter(routeConfig);
