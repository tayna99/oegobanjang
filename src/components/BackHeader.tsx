// 뒤로가기 앱바 — 모바일 풀페이지 화면(2b 검토·2c 승인·2d 이력) 공용 헤더
// (코드리뷰 D 교정: 3개 화면이 동일 마크업을 복제하던 것을 통합 — 터치 타깃·a11y 라벨 단일 관리).
export interface BackHeaderProps {
  title: string;
  onBack: () => void;
}

export function BackHeader({ title, onBack }: BackHeaderProps) {
  return (
    <header className="flex items-center gap-2 border-b border-hairline px-3 py-2.5">
      <button
        type="button"
        aria-label="뒤로"
        onClick={onBack}
        className="flex size-11 items-center justify-center rounded-in text-ink active:bg-surface"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      <h1 className="text-body1 font-bold text-ink">{title}</h1>
    </header>
  );
}
