import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BottomSheet } from '@/components/BottomSheet';
import { Card } from '@/components/Card';
import { Chip } from '@/components/Chip';
import { IconBell } from '@/components/icons';
import { cn } from '@/lib/cn';
import { useSeedNotifications } from '@/lib/dataSeed';
import type { ChipTone } from '@/lib/chipTone';
import { unreadNotificationCount, useNotificationStore } from '@/stores/notificationStore';
import type { NotificationRecord } from '@/lib/api/notifications';
import { resolveDeeplinkPath } from './deeplinkPath';

// 알림 센터 진입점 — R5.4. Shell.tsx의 ThemeToggle/RoleToggle/SettingsLink와 동일하게 자기
// 상태(열림 여부)를 스스로 들고 있는 자기완결 버튼 컴포넌트라, Shell.tsx는 이 컴포넌트를
// 데스크톱 헤더·모바일 플로팅 아이콘 두 자리에 그대로 렌더하기만 하면 된다.
const PRIORITY_TONE: Record<string, ChipTone> = { P1: 'critical', P2: 'medium', P3: 'neutral' };
const PRIORITY_LABEL: Record<string, string> = { P1: '즉시', P2: '오늘', P3: '주간' };

export function NotificationBell({ className }: { className?: string }) {
  // Shell은 인증 여부와 무관하게 항상 마운트되는 최상위 레이아웃이라, 여기서 부르는 것이
  // "앱이 뜨면 항상 한 번은 수신함을 채운다"는 보장을 만드는 가장 단순한 지점이다(mock
  // 모드·비로그인 real 모드는 lib/dataSeed.ts의 가드가 그대로 no-op으로 흡수한다).
  useSeedNotifications();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const records = useNotificationStore((s) => s.records);
  const markRead = useNotificationStore((s) => s.markRead);
  const unreadCount = unreadNotificationCount(records);

  const handleSelect = (notification: NotificationRecord) => {
    setOpen(false);
    if (notification.readAt === null) void markRead(notification.id);
    navigate(resolveDeeplinkPath(notification.deeplinkPath));
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={unreadCount > 0 ? `알림 센터, 읽지 않은 알림 ${unreadCount}건` : '알림 센터'}
        className={cn(
          'relative flex size-12 items-center justify-center rounded-in text-muted transition-colors duration-btn ease-v2 active:bg-surface',
          className,
        )}
      >
        <IconBell width={20} height={20} />
        {unreadCount > 0 && (
          <span className="absolute right-2 top-2 size-1.5 rounded-full bg-critical" aria-hidden="true" />
        )}
      </button>

      <BottomSheet open={open} onClose={() => setOpen(false)}>
        <h2 className="pb-3 pt-1 text-heading2 font-bold text-ink">알림</h2>
        {records.length === 0 ? (
          <p className="pb-6 text-body2 text-subtle">아직 도착한 알림이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2 pb-6">
            {records.map((notification) => (
              <li key={notification.id}>
                <Card
                  interactive
                  onClick={() => handleSelect(notification)}
                  className={cn('flex flex-col gap-1', notification.readAt === null ? 'bg-canvas' : 'bg-surface')}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-label1 font-semibold text-ink">{notification.title}</span>
                    <Chip tone={PRIORITY_TONE[notification.priority] ?? 'neutral'}>
                      {PRIORITY_LABEL[notification.priority] ?? notification.priority}
                    </Chip>
                  </div>
                  <p className="text-body2 text-subtle">{notification.body}</p>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </BottomSheet>
    </>
  );
}
