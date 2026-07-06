export interface OfflineBannerProps {
  lastSyncedAt: string;
}

export function OfflineBanner({ lastSyncedAt }: OfflineBannerProps) {
  return (
    <div className="flex items-center justify-center gap-2 bg-surface px-4 py-2 text-safety text-muted">
      <span className="size-1.5 shrink-0 rounded-full bg-neutral" aria-hidden="true" />
      <span>오프라인 · 마지막 업데이트 {lastSyncedAt}</span>
    </div>
  );
}
