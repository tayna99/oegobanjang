import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Chip } from '@/components/Chip';
import { BottomSheet } from '@/components/BottomSheet';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { useNav } from '@/lib/nav';
import { useRoleStore } from '@/stores/roleStore';
import { DRAFTS } from '@/mocks/drafts';
import type { DraftLangCode } from '@/mocks/drafts';

function findDraft(caseId: string | undefined) {
  return Object.values(DRAFTS).find((draft) => draft.caseId === caseId);
}

export function DraftPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const role = useRoleStore((s) => s.role);
  const draft = findDraft(caseId);
  const [lang, setLang] = useState<DraftLangCode>('ko');
  // R1.7 — 고정 revisedText 토글 대신 실제 편집 가능한 텍스트를 반영한다(실 재생성은 R4).
  // null이면 미적용 상태(원문 표시), 문자열이면 사용자가 시트에서 편집·적용한 결과.
  const [customText, setCustomText] = useState<string | null>(null);
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [revisionDraft, setRevisionDraft] = useState('');

  const activeLang = useMemo(() => {
    if (!draft) return undefined;
    return draft.langs.find((item) => item.lang === lang) ?? draft.langs[0];
  }, [draft, lang]);

  if (!draft || !caseId || !activeLang) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">초안을 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toHome()}>
          오늘 브리핑으로
        </Button>
      </div>
    );
  }

  const revised = customText !== null;
  const text = customText ?? activeLang.text;

  return (
    <div className="p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-heading2 font-semibold text-ink">{draft.title}</h2>
          <p className="mt-1 text-label1 text-muted">{draft.channel} 초안</p>
        </div>
        <Chip tone={revised ? 'positive' : 'approval'}>{revised ? '수정 반영' : '승인 전'}</Chip>
      </div>

      <div className="mb-3 flex gap-2">
        {draft.langs.map((item) => (
          <Button
            key={item.lang}
            size="sm"
            variant={item.lang === activeLang.lang && !revised ? 'primary' : 'outline'}
            onClick={() => {
              setLang(item.lang);
              setCustomText(null);
            }}
          >
            {item.label}
          </Button>
        ))}
      </div>

      <Card className="whitespace-pre-line text-body2 leading-relaxed">{text}</Card>

      <p className="mt-4 rounded-in bg-approvalbg px-3.5 py-3 text-body2 leading-relaxed text-approval">
        승인 전에는 외부 발송이 차단됩니다.
      </p>

      {/* M3 편집 게이트(7단계 §6) — viewer는 읽기 전용, 수정 요청·승인 이동 모두 불가. */}
      {role === 'viewer' ? (
        <p className="mt-4 rounded-in bg-surface px-3.5 py-3 text-body2 text-muted">
          열람자 권한으로는 초안을 읽기만 할 수 있습니다.
        </p>
      ) : (
        <div className="mt-4 flex gap-2.5">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => {
              // 시트를 열 때 부드러운 톤 제안(draft.revisedText)으로 미리 채워, 그대로 쓰거나
              // 직접 고쳐 쓸 수 있게 한다 — "고정 토글"이 아니라 편집 가능한 출발점.
              setRevisionDraft(customText ?? draft.revisedText);
              setRevisionOpen(true);
            }}
          >
            수정 요청
          </Button>
          <Button variant="primary" className="flex-1" onClick={() => nav.toApprove(caseId)}>
            승인 검토로 이동
          </Button>
        </div>
      )}

      <BottomSheet
        open={revisionOpen}
        onClose={() => setRevisionOpen(false)}
        footer={
          <Button
            variant="primary"
            className="w-full"
            disabled={revisionDraft.trim().length === 0}
            onClick={() => {
              setCustomText(revisionDraft.trim());
              setLang('ko');
              setRevisionOpen(false);
            }}
          >
            수정 반영
          </Button>
        }
      >
        <h3 className="mb-2 text-body1 font-semibold">수정 요청 시트</h3>
        <p className="mb-3 text-body2 leading-relaxed text-muted">
          문구를 직접 고쳐 반영합니다. 실제 발송은 승인 이후에도 이 MVP에서 실행하지 않습니다.
        </p>
        <textarea
          value={revisionDraft}
          onChange={(e) => setRevisionDraft(e.target.value)}
          aria-label="수정 요청 문구"
          rows={6}
          className="w-full whitespace-pre-line rounded-in bg-surface px-3.5 py-3 text-label1 leading-relaxed text-ink outline-none focus:ring-2 focus:ring-primary"
        />
      </BottomSheet>
    </div>
  );
}
