import type { ComponentType, SVGProps } from 'react';

export interface SummaryStat {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  label: string;
  count: number;
  unit: string;
  onClick: () => void;
}

export interface SummaryStatRowProps {
  stats: SummaryStat[];
}

// 1단계 스펙 §M1 SummaryStatCard — 무채색 카드, count만 severity 연동 텍스트 컬러 허용
// (여기선 색 지정은 호출부 몫으로 두고 기본 ink만 렌더 — 색 있는 stat이 필요해지면
// count에 className을 추가할 수 있게 이 컴포넌트를 확장한다, 지금은 YAGNI).
export function SummaryStatRow({ stats }: SummaryStatRowProps) {
  return (
    <div className="flex gap-2.5">
      {stats.map(({ icon: Icon, label, count, unit, onClick }) => (
        <button
          key={label}
          type="button"
          onClick={onClick}
          className="flex-1 rounded-chip border border-hairline bg-canvas p-3.5 text-left transition-shadow duration-fast active:shadow-card"
        >
          <Icon width={20} height={20} className="text-muted" />
          <div className="mt-1.5 text-heading2 font-bold tabular-nums">{count}</div>
          <div className="text-caption1 font-medium text-muted">
            <span>{label}</span> <span>{unit}</span>
          </div>
        </button>
      ))}
    </div>
  );
}
