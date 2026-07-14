// 행정사 무인증 링크 뷰(7단계 §1·§4) — Shell(로그인 앱 챙) 바깥의 최상위 라우트. 로그인 없이
// 만료형 링크로 접근하는 유일한 화면이라 PackagePage와 같은 콘텐츠(DocumentPreview)를 그대로
// 재사용하되 nav/tabbar 없이 렌더한다. 이미 얼어붙은 채택 디자인(PC §2d)의 콘텐츠 확장이지
// 새 시각 요소가 아니다 — system-derived 태깅 대상 아님(콘텐츠 자체는 목업 있음).
//
// 구조화된 회신(PC 4e 확장, 2026-07-13) — reference/design-system/외고반장 PC_4a-4f(신규티어)
// .dc.html §4e 이식. 회신은 evidence(package_reply)로 기록된다 — "담당자 케이스에 할일로
// 등록"은 M8 전역 판단 기록(GlobalEvidencePage, evidenceStore를 병합해 보여줌)에서 확인
// 가능한 수준까지만 구현한다(케이스 타임라인 자체는 CASE_SHEETS 정적 데이터라 런타임에
// 새 항목을 추가하는 건 별도 리팩터 — 이번 스코프 밖, 후속 과제로 남긴다).
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/Button';
import { cn } from '@/lib/cn';
import { isLinkExpired } from '@/lib/packageLink';
import { packageFor } from '@/mocks/packages';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { DocumentPreview } from './PackagePage';

type ReplyType = 'supplement' | 'review_done' | 'question';

const REPLY_TYPE_LABEL: Record<ReplyType, string> = {
  supplement: '보완 요청',
  review_done: '검토 완료',
  question: '질문',
};

const QUICK_REQUESTS = [
  '원본 서류가 추가로 필요합니다',
  '재직증명서 원본이 추가로 필요합니다',
  '사유서에 경과 사유 보강이 필요합니다',
];

function StructuredReplyForm({ packageId, recipient }: { packageId: string; recipient: string }) {
  const appendEvidence = useEvidenceStore((s) => s.append);
  const [replyType, setReplyType] = useState<ReplyType>('supplement');
  const [detail, setDetail] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [sent, setSent] = useState(false);

  if (sent) {
    return (
      <section aria-label="구조화된 회신" className="flex flex-col gap-1.5 rounded-in bg-approvalbg px-4 py-3.5">
        <p className="text-label1 font-semibold text-approval">회신을 보냈습니다</p>
        <p className="text-caption1 leading-relaxed text-approval">
          회신은 담당자 케이스에 할일로 등록됩니다. 확인 후 담당자가 연락드립니다.
        </p>
      </section>
    );
  }

  const onSend = () => {
    const trimmed = detail.trim();
    if (!trimmed) return;
    appendEvidence({
      id: `${packageId}-package-reply-${Date.now()}`,
      type: 'package_reply',
      at: new Date().toISOString(),
      caseId: packageId,
      summary: `${recipient} 회신 · ${REPLY_TYPE_LABEL[replyType]} · ${trimmed}${dueDate ? ` (기한 ${dueDate})` : ''}`,
      actor: recipient,
    });
    setSent(true);
  };

  return (
    <section aria-label="구조화된 회신" className="flex flex-col gap-3 rounded-in border border-hairline p-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-label1 font-bold text-ink">구조화된 회신</h2>
        <p className="text-caption1 text-subtle">회신은 담당자 케이스에 할일로 등록됩니다</p>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-caption1 font-semibold text-subtle">회신 유형</span>
        <div className="flex gap-1.5" role="group" aria-label="회신 유형 선택">
          {(Object.keys(REPLY_TYPE_LABEL) as ReplyType[]).map((type) => {
            const active = type === replyType;
            return (
              <button
                key={type}
                type="button"
                aria-pressed={active}
                onClick={() => setReplyType(type)}
                className={cn(
                  'flex-1 rounded-badge px-3 py-2 text-label1 transition-colors duration-btn ease-v2',
                  active ? 'bg-approvalbg font-semibold text-approval shadow-rail-focus' : 'font-medium text-muted shadow-outline hover:bg-surface',
                )}
              >
                {REPLY_TYPE_LABEL[type]}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-caption1 font-semibold text-subtle">자주 쓰는 요청</span>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_REQUESTS.map((text) => (
            <button
              key={text}
              type="button"
              onClick={() => setDetail(text)}
              className="rounded-badge px-2.5 py-1 text-caption1 font-medium text-muted shadow-outline hover:bg-surface"
            >
              {text}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-caption1 font-semibold text-subtle">상세 내용</span>
        <textarea
          value={detail}
          onChange={(event) => setDetail(event.target.value)}
          rows={3}
          aria-label="상세 내용"
          className="rounded-in bg-canvas p-3 text-label1 text-ink shadow-outline outline-none placeholder:text-faint focus:shadow-rail-focus"
          placeholder="담당자에게 전달할 내용을 입력하세요"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-caption1 font-semibold text-subtle">기한 (선택)</span>
        <input
          type="date"
          value={dueDate}
          onChange={(event) => setDueDate(event.target.value)}
          aria-label="회신 기한(선택)"
          className="h-11 w-48 rounded-in bg-canvas px-3 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
        />
      </div>

      <Button variant="primary" className="self-start" disabled={!detail.trim()} onClick={onSend}>
        회신 보내기
      </Button>
      <p className="text-caption1 text-faint">회신 이벤트(package_reply)가 기록됩니다 · 계정 불필요</p>
    </section>
  );
}

export function ExpertLinkPage() {
  const { packageId } = useParams<{ packageId: string }>();
  const pkg = packageFor(packageId);
  const events = useEvidenceStore((s) => s.events);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const logged = useRef(false);

  const expired = pkg ? isLinkExpired(pkg, events) : false;

  // 열람 로그(package_link_viewed) — 만료된 링크는 열람으로 치지 않는다.
  // useRef 가드는 StrictMode 이중 호출 방지용(CaseReviewPage의 review_started와 동일 관례,
  // 단 여기선 "이미 있는 id면 스킵"이 아니라 "이 마운트에서 한 번만" — 재방문마다 새 로그가 남아야 한다).
  useEffect(() => {
    if (!pkg || expired || logged.current) return;
    logged.current = true;
    appendEvidence({
      id: `${pkg.packageId}-link-viewed-${Date.now()}`,
      type: 'package_link_viewed',
      at: new Date().toISOString(),
      caseId: pkg.packageId,
      summary: `행정사가 패키지 링크 열람 · ${pkg.recipient}`,
      actor: pkg.recipient,
    });
  }, [pkg, expired, appendEvidence]);

  if (!pkg) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <p className="text-body2 text-muted">링크를 찾을 수 없습니다.</p>
      </div>
    );
  }

  if (expired) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <div className="max-w-sm rounded-in bg-approvalbg px-5 py-4 text-center">
          <p className="text-label1 font-semibold text-approval">링크가 만료되었습니다</p>
          <p className="mt-1 text-caption1 leading-relaxed text-approval">
            보안을 위해 만료형 링크로만 전달됩니다. 담당자에게 재발급을 요청해주세요.
          </p>
        </div>
      </div>
    );
  }

  const on = new Set(pkg.items.filter((item) => item.defaultOn).map((item) => item.key));

  return (
    <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col gap-5 bg-canvas px-5 py-8">
      <DocumentPreview pkg={pkg} on={on} />
      <StructuredReplyForm packageId={pkg.packageId} recipient={pkg.recipient} />
    </div>
  );
}
