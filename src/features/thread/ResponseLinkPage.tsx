// 근로자 응답 링크(무인증) — R3 stage ②, MESSAGING_CHANNELS.md §3 수신 파이프라인.
// Shell(로그인 앱 챙) 바깥의 최상위 형제 라우트 — ExpertLinkPage(7단계 §1·§4)와 동일한 관례:
// 로그인 없이 만료형 토큰 링크로만 접근한다. 발송 메시지(outbox가 만든 thread_messages
// direction='system')에 심어둔 토큰으로 근로자가 버튼 선택 + 자유입력으로 회신하면, 백엔드가
// 인바운드 정규화(thread_messages inbound) → N02(worker_reply_received) → M6
// Interpretation(proposed)까지 한 번에 처리한다(backend/app/services/response_link.py).
//
// 다국어 번역 파이프라인(LLM)은 이 태스크 범위 밖(R4) — 버튼 라벨은 서버가 내려주는 한국어
// 고정 문구를 그대로 쓴다(RESPONSE_CHOICES, backend/app/services/response_link.py).
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/Button';
import { ApiError } from '@/lib/api/client';
import { fetchResponseLink, submitResponseLink, type ResponseLinkView } from '@/lib/api/threads';

type LoadState = 'loading' | 'expired' | 'ready' | 'error';

export function ResponseLinkPage() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<LoadState>('loading');
  const [view, setView] = useState<ResponseLinkView | null>(null);
  const [choice, setChoice] = useState<string | null>(null);
  const [freeText, setFreeText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchResponseLink(token)
      .then((v) => {
        if (cancelled) return;
        setView(v);
        setState('ready');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setState('expired');
        else setState('error');
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const onSubmit = async () => {
    if (!token || (!choice && !freeText.trim())) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await submitResponseLink(token, { choice: choice ?? undefined, freeText: freeText.trim() || undefined });
      setSubmitted(true);
    } catch {
      setSubmitError('전송에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setSubmitting(false);
    }
  };

  if (state === 'loading') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <p className="text-body2 text-muted">확인 중…</p>
      </div>
    );
  }

  if (state === 'expired') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <div className="max-w-sm rounded-in bg-approvalbg px-5 py-4 text-center">
          <p className="text-label1 font-semibold text-approval">링크가 만료되었습니다</p>
          <p className="mt-1 text-caption1 leading-relaxed text-approval">
            보안을 위해 만료형 링크로만 응답을 받습니다. 담당자에게 새 안내를 요청해주세요.
          </p>
        </div>
      </div>
    );
  }

  if (state === 'error' || !view) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <p className="text-body2 text-muted">링크를 확인할 수 없습니다.</p>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <div className="max-w-sm rounded-in bg-surface px-5 py-4 text-center">
          <p className="text-label1 font-semibold text-ink">응답이 전달되었습니다</p>
          <p className="mt-1 text-caption1 leading-relaxed text-muted">담당자가 확인 후 다시 안내드립니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-screen-sm flex-col gap-5 bg-canvas px-5 py-8">
      <header className="flex flex-col gap-1">
        {view.worker && <p className="text-caption1 text-muted">{view.worker.displayName}님</p>}
        <p className="text-body1 leading-relaxed text-ink">{view.prompt}</p>
      </header>

      <section aria-label="응답 선택" className="flex flex-col gap-2">
        {Object.entries(view.choices).map(([key, label]) => (
          <Button
            key={key}
            type="button"
            variant={choice === key ? 'primary' : 'outline'}
            className="w-full justify-start"
            onClick={() => setChoice(key)}
          >
            {label}
          </Button>
        ))}
      </section>

      <section aria-label="자유 입력" className="flex flex-col gap-1.5">
        <label htmlFor="response-free-text" className="text-caption1 font-semibold text-muted">
          직접 입력(선택)
        </label>
        <textarea
          id="response-free-text"
          value={freeText}
          onChange={(e) => setFreeText(e.target.value)}
          rows={4}
          className="rounded-in border border-hairline bg-surface px-3 py-2 text-body2 text-ink"
          placeholder="추가로 전달하고 싶은 내용을 적어주세요"
        />
      </section>

      {submitError && (
        <p className="rounded-in bg-critbg px-3.5 py-2.5 text-caption1 text-critical" role="alert">
          {submitError}
        </p>
      )}

      <Button
        type="button"
        onClick={onSubmit}
        disabled={submitting || (!choice && !freeText.trim())}
        className="w-full"
      >
        {submitting ? '전송 중…' : '보내기'}
      </Button>
    </div>
  );
}
