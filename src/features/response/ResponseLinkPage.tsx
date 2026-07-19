// 근로자 응답 링크 — Shell 바깥 무인증 단독 페이지(ExpertLinkPage와 동일 관례, 7단계 §4).
// reference/design-system/design-briefs/근로자_응답링크_브리프.md + 목업(외고반장 근로자
// 응답 링크.dc.html) + docs/DESIGN_SYNC_AUDIT_2026-07-17.md §3.
//
// 만료/이미응답/무효 상태는 목업이 베트남어 정적 카피만 제공했다(인터랙티브 데모의 vi/ko
// 토글은 정상→제출완료 흐름에만 연결돼 있었다) — 없는 한국어 번역을 창작하지 않고 목업
// 그대로 베트남어로 둔다(마이크로카피 창작 금지 원칙). "정상"·"제출 완료" 상태만 vi/ko
// 카피 사전이 둘 다 있어 언어 토글이 실제로 동작한다.
//
// 제출은 threadStore.receiveInbound로 인바운드 정규화 지점에 합류한다 — 케이스 상태를
// 직접 바꾸지 않고 M6 해석 큐(interpretationStatus='pending_review')로만 들어간다(isFinal:false
// 계약). messageId를 토큰 기반 고정값으로 둬 재제출이 있어도 멱등(스토어 쪽 no-op)하다.
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useSeedThreads } from '@/lib/dataSeed';
import { RESPONSE_LINK_COPY, responseLinkFor } from '@/mocks/responseLinks';
import { useThreadStore } from '@/stores/threadStore';

type Lang = 'vi' | 'ko';

function ServiceHeader({
  serviceName,
  lang,
  onSetLang,
}: {
  serviceName: string;
  lang?: Lang;
  onSetLang?: (lang: Lang) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-hairline bg-canvas px-5 py-3">
      <div className="flex items-center gap-2">
        <span className="flex size-[22px] items-center justify-center rounded-in bg-primary text-[11px] font-bold text-white">외</span>
        <span className="text-label1 font-semibold text-ink">{serviceName}</span>
      </div>
      {lang && onSetLang && (
        <div className="flex gap-0.5 rounded-in bg-surface p-0.5" role="group" aria-label="언어 선택">
          <button
            type="button"
            aria-pressed={lang === 'vi'}
            onClick={() => onSetLang('vi')}
            className={`h-7 rounded-in px-3 text-caption1 font-semibold transition-all duration-btn ease-v2 ${lang === 'vi' ? 'bg-canvas text-ink shadow-xsmall' : 'text-subtle'}`}
          >
            Tiếng Việt
          </button>
          <button
            type="button"
            aria-pressed={lang === 'ko'}
            onClick={() => onSetLang('ko')}
            className={`h-7 rounded-in px-3 text-caption1 font-semibold transition-all duration-btn ease-v2 ${lang === 'ko' ? 'bg-canvas text-ink shadow-xsmall' : 'text-subtle'}`}
          >
            한국어
          </button>
        </div>
      )}
    </div>
  );
}

// 만료/이미응답/무효 상태는 목업 자체가 베트남어 정적 카피만 제공해 언어 토글이 없다
// (감사 §3.2) — 헤더 서비스명도 그 상태들에서는 베트남어 고정값을 쓴다.
const SERVICE_NAME_VI = 'Ngoại Cao Ban Trưởng';

function CenterIconState({
  tone,
  icon,
  title,
  description,
}: {
  tone: 'warning' | 'approval' | 'neutral';
  icon: 'clock' | 'check' | 'question';
  title: string;
  description: string;
}) {
  const bg = tone === 'warning' ? 'bg-warnbg' : tone === 'approval' ? 'bg-approvalbg' : 'bg-neutbg';
  const fg = tone === 'warning' ? 'text-warning' : tone === 'approval' ? 'text-approval' : 'text-subtle';
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-5 text-center">
      <span className={`flex size-11 items-center justify-center rounded-full ${bg} ${fg}`}>
        {icon === 'clock' && (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
            <path d="M12 7.5V12.5L15 14.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        )}
        {icon === 'check' && (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M6 12.5L10.5 17L18 7.5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
        {icon === 'question' && (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
            <path d="M9 9.5C9 8 10.2 7 12 7s3 1 3 2.5c0 1.8-3 2-3 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="12" cy="16.6" r="1" fill="currentColor" />
          </svg>
        )}
      </span>
      <span className="text-body1 font-bold text-ink">{title}</span>
      <span className="whitespace-pre-line text-caption1 leading-relaxed text-subtle">{description}</span>
    </div>
  );
}

export function ResponseLinkPage() {
  const { token } = useParams<{ token: string }>();
  const fixture = responseLinkFor(token);
  const receiveInbound = useThreadStore((s) => s.receiveInbound);
  // Shell 바깥 형제 라우트라 다른 화면의 useSeedThreads() 트리를 타지 않는다 — 이 페이지가
  // 직접 시딩해 threadStore에 대상 스레드가 존재하도록 보장한다(receiveInbound의
  // "존재하지 않는 스레드" 가드레일에 걸리지 않기 위한 전제 조건).
  useSeedThreads();

  const [lang, setLang] = useState<Lang>(fixture?.lang ?? 'vi');
  const [presetIndex, setPresetIndex] = useState<number | null>(null);
  const [freeText, setFreeText] = useState('');
  const [submitted, setSubmitted] = useState(false);

  // 무효 — 존재 자체 비노출(만료와 구분되는 별도 상태, 감사 §3 가드레일).
  if (!fixture) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col bg-canvas">
        <ServiceHeader serviceName={SERVICE_NAME_VI} />
        <CenterIconState tone="neutral" icon="question" title="Không tìm thấy liên kết" description="Vui lòng kiểm tra lại địa chỉ liên kết." />
      </div>
    );
  }

  if (fixture.state === 'expired') {
    return (
      <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col bg-canvas">
        <ServiceHeader serviceName={SERVICE_NAME_VI} />
        <CenterIconState
          tone="warning"
          icon="clock"
          title="Liên kết đã hết hạn"
          description={'Liên kết này chỉ có hiệu lực trong thời gian nhất định.\nVui lòng liên hệ người quản lý để nhận liên kết mới.'}
        />
      </div>
    );
  }

  if (fixture.state === 'already_replied') {
    return (
      <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col bg-canvas">
        <ServiceHeader serviceName={SERVICE_NAME_VI} />
        <CenterIconState
          tone="approval"
          icon="check"
          title="Đã nhận được câu trả lời"
          description={'Câu trả lời trước đó đã được tiếp nhận.\nKhông cần gửi lại.'}
        />
      </div>
    );
  }

  const copy = RESPONSE_LINK_COPY[lang];
  const canSubmit = presetIndex !== null;
  // submitted는 onSubmit의 canSubmit 가드를 통과해야만 true가 되므로 이 시점엔 presetIndex가
  // 항상 유효하다 — TS가 그 인과관계를 좁히지 못해 별도로 안전하게 파생한다.
  const submittedLabel = presetIndex !== null ? copy.presets[presetIndex] : '';

  if (submitted) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col bg-canvas">
        <ServiceHeader serviceName={copy.serviceName} lang={lang} onSetLang={setLang} />
        <div className="flex flex-1 flex-col items-center gap-3 p-5 pt-10 text-center">
          <span className="flex size-11 items-center justify-center rounded-full bg-succbg text-success">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M6 12.5L10.5 17L18 7.5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="text-body1 font-bold text-ink">{copy.doneTitle}</span>
          <span className="text-caption1 leading-relaxed text-subtle">{copy.doneDesc}</span>
          <div className="flex w-full flex-col gap-1 rounded-in bg-surface px-3.5 py-2.5 text-left">
            <span className="text-caption1 font-semibold text-subtle">{copy.yourReply}</span>
            <span className="text-label1 font-semibold text-ink">{submittedLabel}</span>
            {freeText.trim() && <span className="text-caption1 leading-relaxed text-muted">{freeText.trim()}</span>}
          </div>
          <span className="text-caption1 text-dim">{copy.lockNotice}</span>
        </div>
      </div>
    );
  }

  const onSubmit = () => {
    if (!canSubmit || presetIndex === null) return;
    const body = [copy.presets[presetIndex], freeText.trim()].filter(Boolean).join('\n');
    receiveInbound(fixture.threadId, {
      messageId: `${fixture.token}-reply`,
      body,
      lang,
      at: new Date().toISOString(),
    });
    setSubmitted(true);
  };

  return (
    <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col bg-canvas">
      <ServiceHeader serviceName={copy.serviceName} lang={lang} onSetLang={setLang} />

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
        <div className="flex flex-col gap-2">
          <span className="text-caption1 font-semibold text-subtle">{copy.fromLabel}</span>
          <div className="flex flex-col gap-2.5 rounded-in border border-hairline bg-surface p-4">
            <div className="flex items-center gap-2">
              <span className="flex size-[30px] shrink-0 items-center justify-center rounded-full bg-approvalbg text-caption1 font-bold text-approval">김</span>
              <span className="flex flex-col">
                <span className="text-label1 font-semibold text-ink">{copy.senderName}</span>
                <span className="text-caption1 text-subtle">{copy.senderCompany}</span>
              </span>
            </div>
            <p className="whitespace-pre-line text-label1 leading-relaxed text-ink">{copy.messageBody}</p>
            <div className="flex flex-col gap-1 border-t border-hairline pt-2.5">
              <span className="text-caption1 font-semibold text-muted">{copy.docListTitle}</span>
              <span className="text-caption1 leading-relaxed text-subtle">{copy.docList}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2" role="radiogroup" aria-label={copy.replyLabel}>
          <span className="text-caption1 font-semibold text-subtle">{copy.replyLabel}</span>
          {copy.presets.map((preset, i) => {
            const selected = presetIndex === i;
            return (
              <button
                key={preset}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setPresetIndex(i)}
                className={`flex items-center gap-2.5 rounded-in px-3.5 py-3 text-left transition-all duration-btn ease-v2 ${selected ? 'bg-approvalbg shadow-rail-focus' : 'bg-canvas shadow-outline'}`}
              >
                <span className={`flex size-5 shrink-0 items-center justify-center rounded-full ${selected ? 'shadow-rail-focus' : 'shadow-outline'}`}>
                  {selected && <span className="size-2 rounded-full bg-primary" />}
                </span>
                <span className="text-label1 font-semibold text-ink">{preset}</span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between">
            <span className="text-caption1 font-semibold text-subtle">{copy.freeLabel}</span>
            <span className="text-caption1 text-dim">{copy.optional}</span>
          </div>
          <textarea
            value={freeText}
            onChange={(event) => setFreeText(event.target.value)}
            placeholder={copy.freePlaceholder}
            aria-label={copy.freeLabel}
            className="min-h-[88px] rounded-in bg-canvas p-3.5 text-label1 text-ink shadow-outline outline-none transition-shadow duration-btn ease-v2 placeholder:text-faint focus:shadow-rail-focus"
          />
        </div>

        <p className="rounded-in bg-surface px-3 py-2.5 text-caption1 leading-relaxed text-subtle">{copy.reviewNotice}</p>
      </div>

      <div className="border-t border-hairline bg-canvas p-4 pb-8">
        <button
          type="button"
          onClick={onSubmit}
          disabled={!canSubmit}
          className="h-[50px] w-full rounded-in bg-primary text-label1 font-semibold text-white transition-colors duration-btn ease-v2 disabled:bg-surface disabled:text-faint"
        >
          {copy.submitLabel}
        </button>
      </div>
    </div>
  );
}
