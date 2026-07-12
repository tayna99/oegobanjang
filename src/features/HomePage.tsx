import { useIsDesktop } from '@/lib/useIsDesktop';
import { BriefingHomePage } from '@/features/briefing/BriefingHomePage';
import { ControlTowerPage } from '@/features/control/ControlTowerPage';

// 홈("/") 컨테이너 — 데스크톱은 PC 컨트롤 타워(§3a, 2.5.6), 모바일은 오늘 브리핑(§2a).
// 워크벤치·거버넌스와 동일한 useIsDesktop 렌더 분기 패턴.
export function HomePage() {
  const isDesktop = useIsDesktop();
  return isDesktop ? <ControlTowerPage /> : <BriefingHomePage />;
}
