// OfflineBanner — Montage 공용 컴포넌트.dc.html §4 경고형(2.5.4b 재설계).
// status-cautionary(오렌지) + wifi-off 아이콘 + "재연결 시 자동 동기화" 카피.
// 구 회색형("오프라인 · 마지막 업데이트 …")은 디자인 채택으로 대체 — 블루프린트 §4.
export interface OfflineBannerProps {
  /** 구 시그니처 호환용 — 새 디자인은 표시하지 않는다(재연결 시 자동 동기화가 정본 카피). */
  lastSyncedAt?: string;
  onRetry?: () => void;
}

export function OfflineBanner({ onRetry }: OfflineBannerProps) {
  return (
    <div className="flex items-center gap-2 bg-warnbg px-4 py-2.5">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="shrink-0 text-warning">
        <path
          d="M3 8.5C7 5 17 5 21 8.5M6.5 12C9 10 15 10 17.5 12M10 15.5C11.3 14.5 12.7 14.5 14 15.5"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <path d="M4 4l16 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="19" r="1" fill="currentColor" />
      </svg>
      <span className="flex-1 text-pc-sm leading-snug text-medium">오프라인 상태입니다 · 재연결 시 자동 동기화</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="text-pc-sm font-semibold text-warning underline">
          재시도
        </button>
      )}
    </div>
  );
}
