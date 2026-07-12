import { useIsDesktop } from '@/lib/useIsDesktop';
import { PlaceholderScreen } from '@/screens/PlaceholderScreen';
import { GovernancePage } from './GovernancePage';

// /evidence 컨테이너 — 데스크톱은 PC 거버넌스(§3c, 2.5.5), 모바일은 M8 전역 판단 기록.
// 모바일 M8은 아직 미구현(ROADMAP 2.3, 블루프린트 §9-A: 2d 타임라인·§3c 감사 행 재사용 예정).
export function EvidencePage() {
  const isDesktop = useIsDesktop();
  if (isDesktop) return <GovernancePage />;
  return <PlaceholderScreen name="M8 판단 기록" />;
}
