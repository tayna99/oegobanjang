import { useSyncExternalStore } from 'react';

function subscribe(callback: () => void): () => void {
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
}

function getSnapshot(): boolean {
  return navigator.onLine;
}

// GOTCHAS §1 "오프라인 상태에서 승인 API 호출" 금지 — 승인은 서버 확정 필수. 서버 스냅샷은
// 항상 true(SSR 없음 — 이 앱은 SPA라 실제로 쓰이지 않지만 useSyncExternalStore 계약상 필요).
export function useOnline(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => true);
}
