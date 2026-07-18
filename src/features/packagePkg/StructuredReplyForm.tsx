import { useState } from 'react';
import { Button } from '@/components/Button';
import { API_MODE } from '@/lib/api/config';
import { cn } from '@/lib/cn';
import { useEvidenceStore } from '@/stores/evidenceStore';

// 행정사 구조화된 회신(PC 4e 확장) — 무인증 링크 뷰(ExpertLinkPage)와 화이트라벨 패키지
// 뷰(ExpertPackagePage)가 공유한다. 회신은 evidence(package_reply)로 기록되고, M8 전역
// 판단 기록(GlobalEvidencePage)과 케이스 상세 타임라인(CaseWorkbench.CaseTimeline,
// R0.5) 양쪽에서 확인할 수 있다.
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

export function StructuredReplyForm({ packageId, recipient }: { packageId: string; recipient: string }) {
  const appendEvidence = useEvidenceStore((s) => s.append);
  const [replyType, setReplyType] = useState<ReplyType>('supplement');
  const [detail, setDetail] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [sent, setSent] = useState(false);

  // 코드리뷰 지적(PR #20 P1): package_reply는 무인증 화면 전용이라(PACKAGE_LINK_EVIDENCE_TYPES)
  // 서버에 기록하려면 packages.py가 자기 트랜잭션 안에서 직접 남겨야 하는데, 이번 R2.6엔
  // 회신을 받는 엔드포인트 자체가 없다("패키지 문서 콘텐츠는 범위 밖"). 그런데도 이 폼은
  // real 모드에서도 무조건 "회신을 보냈습니다"를 보여줬다 — 실제로는 그 순간 그 브라우저의
  // 로컬 상태에만 남고 서버 어디에도 저장되지 않아, 새로고침·다른 기기에서 전부 사라진다.
  // 백엔드가 생기기 전까지는 "보냈다"고 거짓으로 확인해주는 것보다, 아직 안 된다고
  // 정직하게 말하는 편이 낫다.
  if (API_MODE === 'real') {
    return (
      <section aria-label="구조화된 회신" className="flex flex-col gap-1.5 rounded-in bg-surface px-4 py-3.5">
        <p className="text-label1 font-semibold text-ink">회신 접수는 아직 준비 중입니다</p>
        <p className="text-caption1 leading-relaxed text-subtle">
          이 기능은 서버에 저장되지 않습니다. 지금은 담당자에게 직접 연락해 전달해주세요.
        </p>
      </section>
    );
  }

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
