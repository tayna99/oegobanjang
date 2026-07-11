export interface BriefingHeaderProps {
  companyName: string;
  date: string;
  unreadNotifications: number;
}

// 오늘 브리핑 헤더 — reference/design-system/외고반장 Mobile.dc.html §2a(36~42행) 이식(M2.6.1).
// 큰 제목 + "날짜 · 사업장" 서브라인 + 알림 벨. (구 v1: 사업장명 + 날짜 칩)
export function BriefingHeader({ companyName, date, unreadNotifications }: BriefingHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-3 py-2">
      <div className="flex flex-col gap-0.5">
        <h1 className="text-heading1 font-bold text-ink">오늘 브리핑</h1>
        <p className="text-pc-sm text-subtle">
          {date} · {companyName}
        </p>
      </div>
      <span className="relative mt-1 flex size-11 items-center justify-center rounded-in text-muted" aria-label="알림">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M6 9a6 6 0 1112 0c0 4 1.5 5.5 1.5 5.5h-15S6 13 6 9z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path d="M10 18.5a2 2 0 004 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        {unreadNotifications > 0 && (
          <span className="absolute right-2 top-2 size-1.5 rounded-full bg-critical" aria-hidden="true" />
        )}
      </span>
    </header>
  );
}
