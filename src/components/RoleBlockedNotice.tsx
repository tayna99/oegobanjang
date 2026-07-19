// 설정 화면군(MembersPage/DelegationPage/SettingsHubPage/NotificationSettingsPage) 권한
// 차단 상태 공용 컴포넌트 — 화면마다 제각각이던 "텍스트 1줄 + 버튼"을 목업(외고반장
// 알림 설정.dc.html)의 원형 배지+제목+부제 패턴으로 통일한다. 화면 전체가 아니라 BackHeader
// 아래 본문 자리만 대체 — 헤더는 차단 상태에서도 계속 보여 뒤로가기를 제공한다(목업과 동일
// 구조, docs/DESIGN_SYNC_AUDIT_2026-07-17.md §5 후속 과제).
import { IconLock } from '@/components/icons';

export interface RoleBlockedNoticeProps {
  title: string;
  subtitle: string;
}

export function RoleBlockedNotice({ title, subtitle }: RoleBlockedNoticeProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2.5 p-5 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-neutbg text-subtle">
        <IconLock width={20} height={20} aria-hidden="true" />
      </span>
      <p className="text-body1 font-bold text-ink">{title}</p>
      <p className="text-caption1 leading-relaxed text-subtle">{subtitle}</p>
    </div>
  );
}
