import { useEffect, useState } from 'react';

// Tailwind lg 브레이크포인트와 동일해야 한다 — Shell의 lg: 분기(탭바/헤더)와
// 워크벤치 렌더 분기가 서로 다른 폭에서 갈라지면 안 되기 때문.
export const DESKTOP_MEDIA_QUERY = '(min-width: 1024px)';

function desktopQuery(): MediaQueryList | undefined {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return undefined;
  return window.matchMedia(DESKTOP_MEDIA_QUERY);
}

// PC 워크벤치(2.5.4)는 CSS hidden이 아니라 이 훅으로 렌더 자체를 분기한다 —
// 모바일에서는 데스크톱 트리가 아예 마운트되지 않아 회귀 여지가 없고,
// jsdom(테스트)에는 matchMedia가 없어 기본 false → 기존 모바일 테스트가 그대로 유효하다.
export function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(() => desktopQuery()?.matches ?? false);

  useEffect(() => {
    const query = desktopQuery();
    if (!query) return;
    // matchMedia change가 표준이지만, 일부 임베디드/에뮬레이션 환경은 이 이벤트를
    // 전달하지 않는 경우가 있어 window resize도 함께 듣고 매번 matches를 재평가한다.
    const sync = () => setIsDesktop(query.matches);
    sync();
    query.addEventListener?.('change', sync);
    window.addEventListener('resize', sync);
    return () => {
      query.removeEventListener?.('change', sync);
      window.removeEventListener('resize', sync);
    };
  }, []);

  return isDesktop;
}
