import { useState } from 'react';
import { USE_REAL_API } from '@/lib/api/config';
import { useAuthActions } from '@/lib/auth';

// O1 — 전화번호 인증 + 승인용 본인확인 설정(7단계 §4). USE_REAL_API가 꺼져 있으면(기본)
// 실제 SMS 백엔드가 없어 인증번호는 "6자리 입력 완료"만 게이트로 삼는다(값 자체를 검증하지
// 않음 — 없는 백엔드를 있는 척하지 않는다). USE_REAL_API가 켜지면(R2.2) 실제 OTP 왕복으로
// 세션을 확립한다 — 전화번호도 그때만 실제 입력 가능해진다(그 전까진 편집 경로 자체가
// 없어야 "값을 검증하지 않는다"는 목업 전제와 모순되지 않는다). "본인확인 사용" 토글은
// 시각적 목업뿐(lib/pin.ts에 저장 슬롯 없음, 실제 PIN 게이트는 승인 화면(ApprovePage)의
// DEMO_PIN 하나로 이미 존재 — 여기서 새 인증 경로를 만들지 않는다).
export interface StepPhoneAuthProps {
  onCodeConfirmedChange: (confirmed: boolean) => void;
}

// 데모 시드 계정(db/seed_demo.sql) — 실 모드 기본 전화번호(김담당·manager).
const DEFAULT_REAL_PHONE = '010-0000-0001';

export function StepPhoneAuth({ onCodeConfirmedChange }: StepPhoneAuthProps) {
  const [codeRequested, setCodeRequested] = useState(false);
  const [code, setCode] = useState('');
  const [bioEnabled, setBioEnabled] = useState(true);
  const [phone, setPhone] = useState(DEFAULT_REAL_PHONE);
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { requestOtp, verifyAndLogin } = useAuthActions();

  const onRequestCode = () => {
    if (!USE_REAL_API) {
      setCodeRequested(true);
      return;
    }
    setError(null);
    requestOtp(phone)
      .then((result) => {
        setDebugCode(result.debugCode);
        setCodeRequested(true);
      })
      .catch(() => setError('인증번호 요청에 실패했습니다. 전화번호를 확인해주세요.'));
  };

  const onChangeCode = (value: string) => {
    const next = value.replace(/\D/g, '').slice(0, 6);
    setCode(next);

    if (!USE_REAL_API) {
      onCodeConfirmedChange(next.length === 6);
      return;
    }

    onCodeConfirmedChange(false); // 실 모드는 verify 성공 시에만 확정한다(값 자체를 게이트로 쓰지 않음).
    if (next.length !== 6) return;
    setError(null);
    verifyAndLogin(phone, next)
      .then(() => onCodeConfirmedChange(true))
      .catch(() => setError('인증번호가 올바르지 않습니다.'));
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-heading1 font-bold text-ink">시작하기</h1>
        <p className="text-body2 text-muted">휴대폰 번호로 시작합니다</p>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-label1 font-semibold text-ink">휴대폰 번호</span>
        <div className="flex h-12 items-center gap-2.5 rounded-in px-3.5 shadow-outline">
          <span className="border-r border-hairline pr-2.5 text-label1 font-semibold text-subtle">+82</span>
          {USE_REAL_API ? (
            <input
              type="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              aria-label="휴대폰 번호"
              className="flex-1 bg-transparent text-label1 text-ink outline-none"
            />
          ) : (
            <span className="text-label1 text-ink">010 1234 5678</span>
          )}
        </div>
        {!codeRequested && (
          <button
            type="button"
            onClick={onRequestCode}
            className="mt-0.5 h-12 rounded-in text-label1 font-semibold text-primary shadow-rail-focus"
          >
            인증번호 받기
          </button>
        )}
      </div>

      {codeRequested && (
        <div className="flex flex-col gap-2">
          <div className="flex items-baseline justify-between">
            <span className="text-label1 font-semibold text-ink">인증번호</span>
            <span className="text-caption1 text-muted">
              {USE_REAL_API && debugCode ? `데모 코드: ${debugCode}` : '문자로 받은 6자리를 입력합니다'}
            </span>
          </div>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(event) => onChangeCode(event.target.value)}
            aria-label="인증번호 6자리"
            className="h-14 rounded-in text-center text-heading2 font-semibold tracking-widest text-ink shadow-outline outline-none focus:shadow-rail-focus"
          />
          {error && (
            <p role="alert" className="text-caption1 text-critical">
              {error}
            </p>
          )}
        </div>
      )}

      <div className="flex flex-col gap-2.5 rounded-in bg-surface p-3.5">
        <div className="flex items-center justify-between gap-3">
          <span className="text-label1 font-semibold text-ink">승인 시 본인확인 사용</span>
          <button
            type="button"
            role="switch"
            aria-checked={bioEnabled}
            aria-label="승인 시 본인확인 사용"
            onClick={() => setBioEnabled((v) => !v)}
            className={`relative h-6 w-11 shrink-0 rounded-full transition-colors duration-btn ease-v2 ${bioEnabled ? 'bg-primary' : 'bg-track'}`}
          >
            <span
              className={`absolute top-0.5 size-5 rounded-full bg-white shadow-lift transition-transform duration-btn ease-v2 ${bioEnabled ? 'translate-x-5' : 'translate-x-0.5'}`}
            />
          </button>
        </div>
        <p className="text-caption1 leading-relaxed text-muted">
          승인 화면에서 생체·PIN을 본인확인 용도로만 사용합니다. 실제 등록은 다음 단계에서 진행합니다.
        </p>
      </div>
    </div>
  );
}
