"use client";

const TAB_ICONS: Record<string, React.ReactNode> = {
  home: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M3 9.5L12 3l9 6.5V21a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  ),
  workers: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.7" />
      <path d="M2 21c0-4 3.134-6 7-6s7 2 7 6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <circle cx="18" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M22 21c0-3-1.5-5-4-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  contact: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 4h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6l-3 3V5a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  ),
  cases: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" stroke="currentColor" strokeWidth="1.7" />
      <path d="M9 8h6M9 12h6M9 16h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  ),
  more: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="5" cy="12" r="1.5" fill="currentColor" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
      <circle cx="19" cy="12" r="1.5" fill="currentColor" />
    </svg>
  ),
};

const TABS = [
  { id: "home",    label: "홈",    badge: 0 },
  { id: "workers", label: "근로자", badge: 0 },
  { id: "contact", label: "컨택",  badge: 2 },
  { id: "cases",   label: "케이스", badge: 0 },
  { id: "more",    label: "더보기", badge: 0 },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function BottomNav({
  activeTab = "home",
  onTabChange,
}: {
  activeTab?: TabId;
  onTabChange?: (id: TabId) => void;
}) {
  return (
    <nav className="mobile-demo-bottom-nav" aria-label="대표 모바일 하단 탭">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={activeTab === tab.id ? "active" : ""}
          onClick={() => onTabChange?.(tab.id)}
          type="button"
          aria-label={tab.label}
          aria-current={activeTab === tab.id ? "page" : undefined}
        >
          <span style={{ position: "relative", display: "inline-flex" }}>
            {TAB_ICONS[tab.id]}
            {tab.badge > 0 ? <span className="tab-badge">{tab.badge}</span> : null}
          </span>
          <span>{tab.label}</span>
        </button>
      ))}
      <i aria-hidden="true" />
    </nav>
  );
}
