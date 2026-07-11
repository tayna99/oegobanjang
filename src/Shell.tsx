import { useEffect, useRef } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/cn';
import { IconBriefing, IconClock, IconFolder, IconMoon, IconMsg, IconSun } from '@/components/icons';
import { ROUTES } from '@/lib/routes';
import { useThemeStore } from '@/stores/themeStore';

const TABS = [
  // 아이콘·색 — Montage 공용 컴포넌트.dc.html §1(2.5.4b): 브리핑=문서형, 케이스=폴더, 기록=시계.
  { to: ROUTES.home, label: '브리핑', Icon: IconBriefing },
  { to: ROUTES.cases(), label: '케이스', Icon: IconFolder },
  { to: ROUTES.messages, label: '메시지', Icon: IconMsg },
  { to: ROUTES.evidence(), label: '기록', Icon: IconClock },
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

// 라이트/다크 전환 버튼 — Montage v2 semantic 토큰이 [data-theme="dark"]로 이미
// 분기돼 있어(tokens.css) 여기서는 토글만 하면 전체 화면이 전환된다(M2.5.1).
function ThemeToggle({ className }: { className?: string }) {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
      className={cn(
        // 터치 타깃 48px(rules/frontend.md) — 아이콘(20px)은 그대로, 히트 영역만 패딩 대신
        // size로 확보(정사각 아이콘 버튼이라 justify/items-center로 중앙 정렬 유지가 더 단순).
        'flex size-12 items-center justify-center rounded-in text-muted transition-colors duration-btn ease-v2 active:bg-surface',
        className,
      )}
    >
      {isDark ? <IconSun width={20} height={20} /> : <IconMoon width={20} height={20} />}
    </button>
  );
}

export function Shell() {
  useDeepLinkBackstack();

  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <header className="hidden h-16 items-center gap-6 border-b border-hairline px-6 lg:flex">
        <span className="text-body1 font-bold">외고반장</span>
        <nav aria-label="주 메뉴" className="flex flex-1 gap-4">
          {TABS.map(({ to, label }) => (
            <NavLink
              key={label}
              to={to}
              end={to === ROUTES.home}
              className={({ isActive }) =>
                cn('text-label1 font-medium', isActive ? 'text-primary' : 'text-muted')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <ThemeToggle />
      </header>

      <div className="fixed right-3 top-3 z-20 lg:hidden">
        <ThemeToggle className="bg-canvas shadow-outline" />
      </div>

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
                // 비활성 탭 = label.alternative(.61) — Montage 공용 컴포넌트 §1 (구 faint .28은 대비 부족)
                isActive ? 'text-primary' : 'text-subtle',
              )
            }
          >
            <Icon width={22} height={22} />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
