// 딥링크 경로 단일 출처 — reference/specs/2단계_알림카탈로그_딥링크맵_v1.md §3을
// SPA 내부 경로로 정규화. router.tsx·nav.ts가 모두 이 표만 참조한다
// (문자열 경로 하드코딩 금지, rules/frontend.md).
export const ROUTES = {
  home: '/',
  cases: (filter?: string) =>
    filter ? `/cases?filter=${encodeURIComponent(filter)}` : '/cases',
  casesImport: '/cases/import', // CSV 일괄 등록(4.4, PC 전용) — 케이스 하위 화면(4b)
  casesWorkers: '/cases/workers', // 근로자 데이터 관리(PC 4b, 신규 최상위 탭 아님)
  casesDispatch: '/cases/dispatch', // 발송 실행 큐(PC 4d, 신규 최상위 탭 아님)
  case: (caseId: string) => `/case/${caseId}`,
  caseDraft: (caseId: string) => `/case/${caseId}/draft`,
  caseApprove: (caseId: string) => `/case/${caseId}/approve`,
  caseHistory: (caseId: string) => `/case/${caseId}/history`, // 2d 승인 이력 (M2.6.4 신설)
  run: (runId: string) => `/run/${runId}`,
  messages: '/messages',
  thread: (threadId: string) => `/thread/${threadId}`,
  evidence: (ref?: string) =>
    ref ? `/evidence?ref=${encodeURIComponent(ref)}` : '/evidence',
  package: (packageId: string) => `/package/${packageId}`,
  // 행정사 무인증 링크(운영급 RBAC 확장). 코드리뷰 지적(PR #20 P1) — real 모드에서는
  // case_id가 아니라 회전하는 link_token이 실제 값이다(mock 모드는 여전히 mocks/packages.ts의
  // packageId를 그대로 쓴다 — 백엔드를 안 거치므로 회전 개념 자체가 없다).
  packageLink: (linkToken: string) => `/link/${linkToken}`,
  // 근로자 응답 링크(무인증, R3 stage ②) — packageLink와 동일 관례. 발송 메시지에 심어둔
  // 회전 토큰으로만 접근한다(MESSAGING_CHANNELS.md §3).
  responseLink: (token: string) => `/r/${token}`,
  expertDashboard: (expertId: string) => `/expert/${expertId}`, // 행정사 화이트라벨 대시보드(7-1)
  expertPackage: (expertId: string, packageId: string) => `/expert/${expertId}/package/${packageId}`,
  done: '/done',
  onboarding: '/onboarding', // Shell 바깥 최상위 형제 라우트(4.1) — packageLinkAbsolute와 동일 관례
  settings: '/settings', // 운영급 RBAC 확장(7단계 §6 "설정")
  settingsMembers: '/settings/members',
  settingsDelegation: '/settings/delegation',
} as const;

// react-router 자식 라우트의 path 세그먼트(선행 슬래시 없음).
export const ROUTE_PATHS = {
  cases: 'cases',
  casesImport: 'cases/import',
  casesWorkers: 'cases/workers',
  casesDispatch: 'cases/dispatch',
  case: 'case/:caseId',
  caseDraft: 'case/:caseId/draft',
  caseApprove: 'case/:caseId/approve',
  caseHistory: 'case/:caseId/history',
  run: 'run/:runId',
  messages: 'messages',
  thread: 'thread/:threadId',
  evidence: 'evidence',
  package: 'package/:packageId',
  done: 'done',
  settings: 'settings',
  settingsMembers: 'settings/members',
  settingsDelegation: 'settings/delegation',
  // Shell 트리 바깥의 최상위 형제 라우트라 절대 경로(무인증 행정사 링크, 7단계 §4).
  packageLinkAbsolute: '/link/:linkToken',
  // 근로자 응답 링크(무인증, R3 stage ②) — 마찬가지로 Shell 바깥 형제 라우트.
  responseLinkAbsolute: '/r/:token',
  // 온보딩도 Shell(로그인 앱 챙) 없이 진행하는 전체 화면 플로우라 형제 라우트로 둔다(4.1).
  onboardingAbsolute: '/onboarding',
  // 행정사 화이트라벨(7-1) — 계정 없이 브랜드 화면으로 접근하는 Shell 바깥 형제 라우트.
  expertDashboardAbsolute: '/expert/:expertId',
  expertPackageAbsolute: '/expert/:expertId/package/:packageId',
} as const;
