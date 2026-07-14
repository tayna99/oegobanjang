import { useIsDesktop } from '@/lib/useIsDesktop';
import { BriefingHomePage } from '@/features/briefing/BriefingHomePage';
import { ControlTowerPage } from '@/features/control/ControlTowerPage';
import { OwnerHomeWorkbench } from '@/features/control/OwnerHomeWorkbench';
import { useRoleStore } from '@/stores/roleStore';

// 홈("/") 컨테이너 — 데스크톱은 PC 컨트롤 타워(§3a, 2.5.6), 모바일은 오늘 브리핑(§2a).
// 워크벤치·거버넌스와 동일한 useIsDesktop 렌더 분기 패턴. owner는 PC에서 담당자의 풍부한
// 운영 화면 대신 최소화면(4f)을 본다 — "승인은 모바일에서"(7단계 §2 각주3).
export function HomePage() {
  const isDesktop = useIsDesktop();
  const role = useRoleStore((s) => s.role);
  if (!isDesktop) return <BriefingHomePage />;
  return role === 'owner' ? <OwnerHomeWorkbench /> : <ControlTowerPage />;
}
