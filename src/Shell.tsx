import { useEffect, useRef } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/cn';
import { IconDoc, IconHome, IconList, IconMsg } from '@/components/icons';
import { countArrivedResponses } from '@/lib/threads';
import { ROUTES } from '@/lib/routes';
import { useThreadStore } from '@/stores/threadStore';

const TABS = [
  { to: ROUTES.home, label: '브리핑', Icon: IconHome },
  { to: ROUTES.cases(), label: '케이스', Icon: IconList },
  { to: ROUTES.messages, label: '메시지', Icon: IconMsg },
  { to: ROUTES.evidence(), label: '기록', Icon: IconDoc },
] as const;

// 딥링크로 바로 진입한 경우(최초 위치가 '/'가 아님) 백스택을 M1 → 목적지로
// 재구성한다. location.key === 'default'는 react-router가 클라이언트
// 내비게이션 없이 "처음 로드된 위치"에만 부여하는 값이라, 앱 내부에서
// 링크를 눌러 이동한 경우와 구분할 수 있는 신뢰할 수 있는 신호다
// (2단계_알림카탈로그_딥링크맵_v1.md §3 공통 규칙).
function useDeepLinkBackstack() {
  const navigate = useNavigate();
  const location = useLocation();
  const synced = useRef(false);

  useEffect(() => {
    if (synced.current) return;
    synced.current = true;
    if (location.key !== 'default' || location.pathname === '/') return;
    const target = `${location.pathname}${location.search}`;
    navigate(ROUTES.home, { replace: true });
    navigate(target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

export function Shell() {
  useDeepLinkBackstack();
  // 메시지 탭 도트 인디케이터 — threadStore 파생값은 lib/threads.ts의 selector 하나로만
  // 계산한다(rules/frontend.md "파생값은 selector로").
  const hasArrivedResponses = useThreadStore(
    (s) => countArrivedResponses(Object.values(s.threads)) > 0,
  );

  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <header className="hidden h-16 items-center gap-6 border-b border-hairline px-6 lg:flex">
        <span className="text-base font-bold">외고반장</span>
        <nav aria-label="주 메뉴" className="flex gap-4">
          {TABS.map(({ to, label }) => (
            <NavLink
              key={label}
              to={to}
              end={to === ROUTES.home}
              className={({ isActive }) =>
                cn('text-sm font-medium', isActive ? 'text-primary' : 'text-muted')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="pb-tabbar lg:pb-0">
        <Outlet />
      </main>

      <nav
        aria-label="모바일 탭바"
        className="fixed inset-x-0 bottom-0 z-10 flex h-tabbar border-t border-hairline bg-canvas lg:hidden"
      >
        {TABS.map(({ to, label, Icon }) => (
          <NavLink
            key={label}
            to={to}
            end={to === ROUTES.home}
            className={({ isActive }) =>
              cn(
                'flex flex-1 flex-col items-center justify-center gap-1 text-tabbar-label font-semibold',
                isActive ? 'text-primary' : 'text-faint',
              )
            }
          >
            <span className="relative inline-flex">
              <Icon width={22} height={22} />
              {to === ROUTES.messages && hasArrivedResponses && (
                <span
                  aria-hidden="true"
                  data-testid="tab-messages-dot"
                  className="absolute -right-0.5 -top-0.5 h-dot w-dot rounded-full bg-info"
                />
              )}
            </span>
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
