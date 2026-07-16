import { calcDday } from '@/lib/dday';
import type { EvidenceEvent } from '@/types';
import type { HandoffPackage } from '@/mocks/packages';

// 행정사 패키지 링크(7단계 §4 "만료형(기본 7일) + 열람 로그. 재발급은 manager").
export const LINK_VALIDITY_DAYS = 7;
// 앱 전역이 공유하는 고정 데모 "오늘"(BriefingHomePage/ControlTowerPage의 "7월 10일" 기준) —
// evidence 타임스탬프(new Date().toISOString(), 실제 벽시계)와 달리 데모 세계관의 날짜다.
export const DEMO_TODAY = '2026-07-10';

// 재발급 이후엔 원본 발급일 계산과 무관하게 항상 유효(데모 세션 동안) — 실제 벽시계와
// 고정 데모 날짜가 섞이는 걸 피하려고 "재발급 이벤트 존재 여부"만으로 판정한다.
export function isLinkExpired(pkg: HandoffPackage, events: readonly EvidenceEvent[]): boolean {
  const reissued = events.some((e) => e.type === 'package_link_issued' && e.caseId === pkg.packageId);
  if (reissued) return false;
  return calcDday(DEMO_TODAY, pkg.createdAt) > LINK_VALIDITY_DAYS;
}
