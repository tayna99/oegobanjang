import { useState } from 'react';
import { API_MODE } from '@/lib/api/config';
import { useSessionStore } from '@/stores/sessionStore';

// O1 — 전화번호 인증 + 승인용 본인확인 설정(7단계 §4).
// mock 모드(기본값): 실 SMS 백엔드가 없어 인증번호는 "6자리 입력 완료"만 게이트로 삼는다
// (값 자체를 검증하지 않음 — 없는 백엔드를 있는 척하지 않는다).
// real 모드(R2.2, VITE_API_MODE=real): sessionStore를 통해 backend/app/api/v1/auth.py의
// 실제 OTP request/verify를 호출한다 — 성공하면 세션이 서고 roleStore가 실제 멤버십
// 역할로 갱신된다(NEXT_ROADMAP M-6 "새로고침 시 manager 복귀" 문제의 해소 지점).
// "본인확인 사용" 토글은 두 모드 모두 시각적 목업뿐(lib/pin.ts에 저장 슬롯 없음, 실제 PIN
// 게이트는 승인 화면(ApprovePage)의 DEMO_PIN 하나로 이미 존재 — 여기서 새 인증 경로를 만들지 않는다).
export interface StepPhoneAuthProps {
  onCodeConfirmedChange: (confirmed: boolean) => void;
}

// 시드된 담당자 계정(backend db/seed_demo.sql) — real 모드에서 어떤 번호로 로그인할 수
// 있는지 알려주는 placeholder 힌트일 뿐, 값을 미리 채워 넣지 않는다.
const DEMO_PHONE_HINT = '010-0000-0001';

export function StepPhoneAuth({ onCodeConfirmedChange }: StepPhoneAuthProps) {
  const isReal = API_MODE === 'real';
  const requestOtpAction = useSessionStore((s) => s.requestOtp);
  const verifyOtpAction = useSessionStore((s) => s.verifyOtp);
  const sessionError = useSessionStore((s) => s.error);
  const sessionStatus = useSessionStore((s) => s.status);

  const [phone, setPhone] = useState('');
  const [codeRequested, setCodeRequested] = useState(false);
  const [code, setCode] = useState('');
  const [bioEnabled, setBioEnabled] = useState(true);
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [requesting, setRequesting] = useState(false);

  const handleRequestCode = async () => {
    if (!isReal) {
      setCodeRequested(true);
      return;
    }
    setRequesting(true);
    try {
      const result = await requestOtpAction(phone);
      setDebugCode(result.debugCode);
      setCodeRequested(true);
    } catch {
      // 실패 사유는 sessionError(사용자 노출용)에 이미 담겨 있다 — 아래에서 렌더.
    } finally {
      setRequesting(false);
    }
  };

  const handleCodeChange = async (raw: string) => {
    const next = raw.replace(/\D/g, '').slice(0, 6);
    setCode(next);
    if (!isReal) {
      onCodeConfirmedChange(next.length === 6);
      return;
    }
    onCodeConfirmedChange(false);
    if (next.length === 6) {
      try {
        await verifyOtpAction(phone, next);
        onCodeConfirmedChange(true);
      } catch {
        onCodeConfirmedChange(false);
      }
    }
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
          {isReal ? (
            <input
              type="tel"
              inputMode="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              // 코드리뷰 지적: 인증번호를 요청한 뒤에도 번호를 계속 편집할 수 있으면, 검증 시점의
              // 번호가 실제로 OTP를 요청한 번호와 달라져 "코드는 맞는데 번호가 달라 실패"하는
              // 혼란스러운 상태가 된다 — 요청 이후엔 잠근다.
              disabled={isReal && codeRequested}
              placeholder={DEMO_PHONE_HINT}
              aria-label="휴대폰 번호"
              className="flex-1 bg-transparent text-label1 text-ink outline-none placeholder:text-faint disabled:text-faint"
            />
          ) : (
            <span className="text-label1 text-ink">010 1234 5678</span>
          )}
        </div>
        {!codeRequested && (
          <button
            type="button"
            onClick={handleRequestCode}
            disabled={isReal && (requesting || phone.trim().length === 0)}
            className="mt-0.5 h-12 rounded-in text-label1 font-semibold text-primary shadow-rail-focus disabled:text-faint"
          >
            인증번호 받기
          </button>
        )}
        {/* 코드리뷰 지적: 요청 단계 실패(잘못된 번호 형식·backend 다운·rate limit 등)는
            codeRequested가 true로 안 바뀌어 아래 블록이 마운트조차 안 됐다 — 그 결과 버튼만
            스피너가 멈추고 사용자는 왜 실패했는지 전혀 알 수 없었다. 요청 단계 에러는 여기,
            블록 밖에서 항상 렌더한다. */}
        {isReal && !codeRequested && sessionError && (
          <p className="text-caption1 text-critical-text">{sessionError}</p>
        )}
      </div>

      {codeRequested && (
        <div className="flex flex-col gap-2">
          <div className="flex items-baseline justify-between">
            <span className="text-label1 font-semibold text-ink">인증번호</span>
            <span className="text-caption1 text-muted">문자로 받은 6자리를 입력합니다</span>
          </div>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(event) => handleCodeChange(event.target.value)}
            disabled={isReal && sessionStatus === 'authenticating'}
            aria-label="인증번호 6자리"
            className="h-14 rounded-in text-center text-heading2 font-semibold tracking-widest text-ink shadow-outline outline-none focus:shadow-rail-focus disabled:text-faint"
          />
          {isReal && debugCode && (
            <p className="text-caption1 text-muted">개발용 인증번호(실 SMS 미연동): {debugCode}</p>
          )}
          {isReal && sessionStatus === 'authenticating' && (
            <p className="text-caption1 text-muted">확인 중…</p>
          )}
          {isReal && sessionError && <p className="text-caption1 text-critical-text">{sessionError}</p>}
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
