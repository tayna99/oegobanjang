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
  const [revised, setRevised] = useState(false);
  const [revisionOpen, setRevisionOpen] = useState(false);

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

  const text = revised ? draft.revisedText : activeLang.text;

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
              setRevised(false);
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
          <Button variant="outline" className="flex-1" onClick={() => setRevisionOpen(true)}>
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
            onClick={() => {
              setRevised(true);
              setLang('ko');
              setRevisionOpen(false);
            }}
          >
            부드럽게 다듬기
          </Button>
        }
      >
        <h3 className="mb-2 text-body1 font-semibold">수정 요청 시트</h3>
        <p className="mb-4 text-body2 leading-relaxed text-muted">
          근로자에게 더 부드럽게 들리도록 요청 문장을 다듬습니다. 실제 발송은 승인 이후에도 이 MVP에서 실행하지 않습니다.
        </p>
        <div className="rounded-in bg-surface px-3.5 py-3 text-label1 leading-relaxed">
          요청 톤: 정중하고 부담이 적은 문장
        </div>
      </BottomSheet>
    </div>
  );
}
