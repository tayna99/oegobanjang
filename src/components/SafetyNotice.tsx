// SafetyNotice — Montage 공용 컴포넌트.dc.html §3 (2.5.4b에서 2형으로 확장).
// neutral: 고정 문구 전용. GOTCHAS §3 "승인 전에는 외부 발송이 차단됩니다." 문구는
// 글자 하나도 바꾸지 않는다 — neutral은 children을 받지 않아 호출부가 문구를 바꿀 수 없다.
// emphasis: 경고 변형(오렌지) — 상황 문구를 children으로 받는다(예: 미승인 24시간 경과).
import type { ReactNode } from 'react';
import { IconShield } from '@/components/icons';

function IconWarnTriangle() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="shrink-0">
      <path d="M12 3l9 16H3l9-16z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M12 10v3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="16.5" r="0.9" fill="currentColor" />
    </svg>
  );
}

// 고정 문구의 단일 출처 — 다른 화면(2c 배너 등)이 문구를 다시 타이핑하지 않고 이 상수를 쓴다.
export const SAFETY_NOTICE_TEXT = '승인 전에는 외부 발송이 차단됩니다.';

export function SafetyNotice() {
  return (
    <div className="flex items-center justify-center gap-safety-gap rounded-in bg-surface px-3.5 py-3 text-safety text-subtle">
      <IconShield width={15} height={15} className="shrink-0 text-primary" />
      <span>{SAFETY_NOTICE_TEXT}</span>
    </div>
  );
}

export function SafetyNoticeEmphasis({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center justify-center gap-safety-gap rounded-in bg-warnbg px-3.5 py-3 text-safety font-medium text-warning">
      <IconWarnTriangle />
      <span>{children}</span>
    </div>
  );
}
