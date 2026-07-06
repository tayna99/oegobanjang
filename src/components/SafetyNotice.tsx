// SafetyNotice — 프로토타입 v3 .safety 클래스(reference/prototype_v3.html §86-88) 이식.
// GOTCHAS §3: "승인 전에는 외부 발송이 차단됩니다." 문구는 글자 하나도 바꾸지 않는다.
// props로 텍스트를 받지 않는 파라미터 없는 컴포넌트로 만들어 호출부가 문구를 바꿀 수 없게 막는다.
import { IconShield } from '@/components/icons';

export function SafetyNotice() {
  return (
    <div className="flex items-center gap-safety-gap rounded-chip bg-surface px-3.5 py-3 text-safety">
      <IconShield width={15} height={15} className="shrink-0 text-primary" />
      <span>승인 전에는 외부 발송이 차단됩니다.</span>
    </div>
  );
}
