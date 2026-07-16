import { cn } from '@/lib/cn';

export interface KpiTileProps {
  label: string;
  value: number;
  tone: string;
  className?: string;
}

// GovernancePage(§3c)·ControlTowerPage(§3a)에 거의 동일하게 중복 정의돼 있던 걸 통합(GOTCHAS §4).
export function KpiTile({ label, value, tone, className }: KpiTileProps) {
  return (
    <div className={cn('flex flex-col gap-1 rounded-in border border-hairline bg-canvas px-3.5 py-3', className)}>
      <span className="text-pc-2xs text-subtle">{label}</span>
      <span className={cn('text-heading2 font-bold tabular-nums', tone)}>{value}</span>
    </div>
  );
}
