import type { ExpertAccount } from '@/types';

// 화이트라벨 헤더(7-1) — 외고반장 브랜드 대신 행정사무소 브랜드(로고 이니셜 + 이름)를 얹는다.
// brandColor는 행정사 제공 데이터(업로드 로고와 동급)라 인라인 style로만 적용한다 —
// 디자인 토큰이 아니라 테넌트/expert별 커스텀 값. 하단 "외고반장 제공"은 powered-by 관례.
export interface ExpertBrandHeaderProps {
  account: ExpertAccount;
  subtitle?: string;
  onBack?: () => void;
}

export function ExpertBrandHeader({ account, subtitle, onBack }: ExpertBrandHeaderProps) {
  return (
    <header className="flex items-center gap-3 border-b border-hairline pb-4">
      {onBack && (
        <button
          type="button"
          aria-label="대시보드로"
          onClick={onBack}
          className="flex size-9 shrink-0 items-center justify-center rounded-in text-ink active:bg-surface"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      )}
      <span
        aria-hidden="true"
        className="flex size-9 shrink-0 items-center justify-center rounded-in text-label1 font-bold text-white"
        style={{ backgroundColor: account.brandColor }}
      >
        {account.brandInitial}
      </span>
      <div className="flex min-w-0 flex-col">
        <span className="truncate text-body1 font-bold text-ink">{account.officeName}</span>
        {subtitle && <span className="truncate text-caption1 text-subtle">{subtitle}</span>}
      </div>
      <span className="ml-auto shrink-0 text-caption1 text-faint">외고반장 제공</span>
    </header>
  );
}
