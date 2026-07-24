import { IconLock } from '@/components/icons';
import { cn } from '@/lib/cn';

// 온보딩 O1(StepPhoneAuth "본인확인 사용")에 있던 pill 스위치 마크업을 공용 컴포넌트로
// 추출했다(2026-07-17, 알림 설정 화면 신설 계기 — GOTCHAS §4 "같은 목적의 컴포넌트를 두 번
// 만들지 않는다"). locked=true는 "항상 ON, 끌 수 없음" 전용 표시(설정 § 알림의 "승인 요청
// 즉시 알림") — 값을 바꿀 수 없으므로 onChange를 아예 호출하지 않는다.
export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  locked?: boolean;
}

export function Toggle({ checked, onChange, label, locked = false }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={locked}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative h-6 w-11 shrink-0 rounded-full transition-colors duration-btn ease-v2',
        locked ? 'bg-toggleLocked cursor-default' : checked ? 'bg-primary' : 'bg-track',
      )}
    >
      <span
        className={cn(
          'absolute top-0.5 flex size-5 items-center justify-center rounded-full bg-white shadow-lift transition-transform duration-btn ease-v2',
          checked ? 'translate-x-5' : 'translate-x-0.5',
        )}
      >
        {locked && <IconLock width={10} height={10} className="text-faint" aria-hidden="true" />}
      </span>
    </button>
  );
}
