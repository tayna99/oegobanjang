// 딥링크 경로 단일 출처 — reference/specs/2단계_알림카탈로그_딥링크맵_v1.md §3을
// SPA 내부 경로로 정규화. router.tsx·nav.ts가 모두 이 표만 참조한다
// (문자열 경로 하드코딩 금지, rules/frontend.md).
export const ROUTES = {
  home: '/',
  cases: (filter?: string) =>
    filter ? `/cases?filter=${encodeURIComponent(filter)}` : '/cases',
  case: (caseId: string) => `/case/${caseId}`,
  caseDraft: (caseId: string) => `/case/${caseId}/draft`,
  caseApprove: (caseId: string) => `/case/${caseId}/approve`,
  run: (runId: string) => `/run/${runId}`,
  messages: '/messages',
  thread: (threadId: string) => `/thread/${threadId}`,
  evidence: (ref?: string) =>
    ref ? `/evidence?ref=${encodeURIComponent(ref)}` : '/evidence',
  package: (packageId: string) => `/package/${packageId}`,
  done: '/done',
  onboardingWorkers: '/onboarding/workers',
} as const;

// react-router 자식 라우트의 path 세그먼트(선행 슬래시 없음).
export const ROUTE_PATHS = {
  cases: 'cases',
  case: 'case/:caseId',
  caseDraft: 'case/:caseId/draft',
  caseApprove: 'case/:caseId/approve',
  run: 'run/:runId',
  messages: 'messages',
  thread: 'thread/:threadId',
  evidence: 'evidence',
  package: 'package/:packageId',
  done: 'done',
  onboardingWorkers: 'onboarding/workers',
} as const;
