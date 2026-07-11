export interface BriefingHeaderProps {
  companyName: string;
  date: string;
  unreadNotifications: number;
}

// 1단계 스펙 §M1 BriefingHeader — 사업장명·날짜·알림 아이콘·프로필(역할 전환).
// 역할 전환 UI는 4.2(권한 모델)에서 실제 role 소스와 함께 붙인다.
export function BriefingHeader({ companyName, date, unreadNotifications }: BriefingHeaderProps) {
  return (
    <header className="flex items-center justify-between gap-3 py-2">
      <span className="text-body1 font-bold">{companyName}</span>
      <span className="rounded-chip border border-hairline px-3 py-1.5 text-label1 font-semibold text-muted">
        {date}
        {unreadNotifications > 0 && (
          <span className="ml-1.5 inline-block size-1.5 rounded-full bg-critical align-middle" aria-hidden="true" />
        )}
      </span>
    </header>
  );
}
