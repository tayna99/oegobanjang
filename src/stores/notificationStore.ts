import { create } from 'zustand';
import { markNotificationRead } from '@/lib/api/notifications';
import type { NotificationRecord } from '@/lib/api/notifications';

// 알림 센터 스토어 — R5.4. mock 모드는 절대 채우지 않는다(useSeedNotifications이 API_MODE==='real'
// 일 때만 hydrate를 부른다, lib/dataSeed.ts) — 그래서 BriefingHomePage의 unreadNotifications는
// mock 모드에서 항상 이 스토어의 초기값(빈 배열 → 0)을 본다(동작 무변경 보장).
interface NotificationStoreState {
  records: NotificationRecord[];
  /** real 모드 부팅 시(useSeedNotifications) 서버 응답으로 전량 교체 — citationStore.hydrate와
   * 동일 원칙(감사 게이트가 아니므로 병합 대신 단순 교체). */
  hydrate: (records: NotificationRecord[]) => void;
  /** 알림 센터에서 항목을 열람했을 때 — 서버 확인 후 로컬 레코드를 그 응답으로 교체한다
   * (승인처럼 서버 확정 후 반영 원칙을 굳이 강제할 감사 게이트는 아니지만, 낙관적으로
   * 먼저 지역 상태를 바꾸지 않는 쪽이 실패 시 "읽음 표시가 됐는데 서버는 모른다"는 불일치를
   * 만들지 않는다). 실패하면 로컬 상태는 그대로 두고 콘솔에만 남긴다.
   */
  markRead: (id: string) => Promise<void>;
  reset: () => void;
}

export const useNotificationStore = create<NotificationStoreState>((set) => ({
  records: [],
  hydrate: (records) => set({ records }),
  markRead: async (id) => {
    try {
      const updated = await markNotificationRead(id);
      set((s) => ({ records: s.records.map((r) => (r.id === id ? updated : r)) }));
    } catch (err) {
      console.error('[notificationStore] 읽음 처리 실패', err);
    }
  },
  reset: () => set({ records: [] }),
}));

export function unreadNotificationCount(records: readonly NotificationRecord[]): number {
  return records.filter((r) => r.readAt === null).length;
}
