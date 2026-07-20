import { ROUTES } from '@/lib/routes';

// notifications.deeplink_path(백엔드가 2단계_알림카탈로그_딥링크맵_v1.md §3 스킴 그대로
// 저장한 값, 예: 'case/cs1/approve')을 이 앱의 SPA 내부 경로로 정규화한다. 카탈로그 path와
// 이 앱의 라우트는 대부분 1:1이라('case/{id}(/approve)' 등은 선행 슬래시만 붙이면 된다) —
// 세그먼트 이름이 다른 세 갈래(§3 표: briefing→M1, response/{threadId}→M6, evidence/{eventId}
// →M8)만 표로 변환한다. rules/frontend.md "문자열 경로 하드코딩 금지"를 지키려고 변환
// 결과는 항상 lib/routes.ts의 ROUTES.*를 거친다.
export function resolveDeeplinkPath(path: string): string {
  if (path === 'briefing') return ROUTES.home;
  if (path === 'onboarding/workers') return ROUTES.onboarding;

  const responseMatch = /^response\/(.+)$/.exec(path);
  if (responseMatch) return ROUTES.thread(responseMatch[1]);

  const evidenceMatch = /^evidence\/(.+)$/.exec(path);
  if (evidenceMatch) return ROUTES.evidence(evidenceMatch[1]);

  return `/${path}`;
}
