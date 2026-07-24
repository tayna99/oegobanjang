import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Chip } from '@/components/Chip';
import { BottomSheet } from '@/components/BottomSheet';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { API_MODE } from '@/lib/api/config';
import { fetchCaseDraft, type Draft as ApiDraft } from '@/lib/api/drafts';
import { useNav } from '@/lib/nav';
import { useRoleStore } from '@/stores/roleStore';
import { DRAFTS } from '@/mocks/drafts';

function findDraft(caseId: string | undefined) {
  return Object.values(DRAFTS).find((draft) => draft.caseId === caseId);
}

// 언어 탭 하나의 최소 모양 — mock(DraftFixture.langs)과 real(fetchCaseDraft) 두 출처를
// 이 공용 모양으로 합쳐 아래 렌더 로직이 출처를 몰라도 되게 한다.
interface LangTab {
  lang: string;
  label: string;
  text: string;
}

export function DraftPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const nav = useNav();
  const role = useRoleStore((s) => s.role);
  const mockDraft = API_MODE !== 'real' ? findDraft(caseId) : undefined;

  // SD-5 — real 모드는 mocks/drafts.ts 대신 GET /api/v1/cases/{id}/draft에서 시드 초안을
  // 가져온다. mock 모드는 이 상태를 전혀 건드리지 않는다(기존 동작 100% 보존).
  const [realDraft, setRealDraft] = useState<ApiDraft | null>(null);
  const [draftLoading, setDraftLoading] = useState(API_MODE === 'real');

  useEffect(() => {
    if (API_MODE !== 'real' || !caseId) return;
    let cancelled = false;
    setDraftLoading(true);
    fetchCaseDraft(caseId)
      .then((draft) => {
        if (!cancelled) setRealDraft(draft);
      })
      .catch((err: unknown) => {
        if (!cancelled) console.error('[DraftPage] 초안 조회 실패', err);
      })
      .finally(() => {
        if (!cancelled) setDraftLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const [lang, setLang] = useState<string>('ko');
  // R1.7 — 고정 revisedText 토글 대신 실제 편집 가능한 텍스트를 반영한다(실 재생성은 R4).
  // null이면 미적용 상태(원문 표시), 문자열이면 사용자가 시트에서 편집·적용한 결과.
  const [customText, setCustomText] = useState<string | null>(null);
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [revisionDraft, setRevisionDraft] = useState('');

  // real 모드는 draft_variants.is_revised=true 행(이미 적용된 수정본의 DB 이력)을 언어 탭에서
  // 제외한다 — mock의 langs가 항상 원본만 담고 "수정"은 이 화면의 로컬 상태(customText)로만
  // 표현하는 것과 동일한 모델을 유지하기 위해서다(정직한 단순화, 서버가 실제로 사용자의 수정을
  // 새 변형으로 저장하게 되면 재검토 대상). 전부 is_revised인 이론상 엣지케이스는 그대로 노출한다.
  const tabs: LangTab[] = useMemo(() => {
    if (API_MODE === 'real') {
      if (!realDraft) return [];
      const original = realDraft.langs.filter((item) => !item.isRevised);
      const source = original.length > 0 ? original : realDraft.langs;
      return source.map((item) => ({ lang: item.lang, label: item.label, text: item.text }));
    }
    return mockDraft?.langs.map((item) => ({ lang: item.lang, label: item.label, text: item.text })) ?? [];
  }, [mockDraft, realDraft]);

  const activeTab = useMemo(() => tabs.find((item) => item.lang === lang) ?? tabs[0], [tabs, lang]);

  if (!caseId) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">초안을 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toHome()}>
          오늘 브리핑으로
        </Button>
      </div>
    );
  }

  if (API_MODE === 'real' && draftLoading) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">불러오는 중…</p>
      </div>
    );
  }

  if (!activeTab) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">초안을 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toHome()}>
          오늘 브리핑으로
        </Button>
      </div>
    );
  }

  const title = API_MODE === 'real' ? (realDraft?.purpose ?? '') : (mockDraft?.title ?? '');
  const channel = API_MODE === 'real' ? (realDraft?.channel ?? '') : (mockDraft?.channel ?? '');
  const revised = customText !== null;
  const text = customText ?? activeTab.text;

  return (
    <div className="p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-heading2 font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-label1 text-muted">{channel} 초안</p>
        </div>
        <Chip tone={revised ? 'positive' : 'approval'}>{revised ? '수정 반영' : '승인 전'}</Chip>
      </div>

      <div className="mb-3 flex gap-2">
        {tabs.map((item) => (
          <Button
            key={item.lang}
            size="sm"
            variant={item.lang === activeTab.lang && !revised ? 'primary' : 'outline'}
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
              // 시트를 열 때 부드러운 톤 제안으로 미리 채워, 그대로 쓰거나 직접 고쳐 쓸 수 있게
              // 한다 — "고정 토글"이 아니라 편집 가능한 출발점. mock은 DRAFTS의 고정 revisedText,
              // real은 서버에 그 컬럼이 없어(설계 결정, plans/SEED_DESIGN_2026-07-20.md Part B5(b))
              // 현재 활성 언어의 원문으로 대신 채운다(정직한 단순화).
              setRevisionDraft(customText ?? (mockDraft?.revisedText ?? activeTab.text));
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
              setLang(activeTab.lang);
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
