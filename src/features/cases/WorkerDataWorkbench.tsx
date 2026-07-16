import { useEffect } from 'react';
import { Button } from '@/components/Button';
import { IconDoc } from '@/components/icons';
import { dDayLabel, dDayTextClass } from '@/lib/dday';
import { useNav } from '@/lib/nav';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useRoleStore } from '@/stores/roleStore';

// 근로자 데이터 관리(PC 4b) — reference/design-system/외고반장 PC_4a-4f(신규티어).dc.html
// §4b(135~239행) 이식. "케이스는 여기서 파생" — 이 앱엔 별도 워커 엔티티가 없어(GOTCHAS,
// 온보딩/CSV와 동일 결정) 근로자 목록 = workerRef가 있는 CaseCard 전체를 그대로 보여준다.
// 서류 스캔 자동분류는 OCR 파이프라인이 없어 정적 안내 카드로만 남긴다(순신규 분류, 2026-07-13
// 델타 감사 §3 — "확인 대기" 상태까지만 그림, 실제 분류 로직은 후속).
export function WorkerDataWorkbench() {
  const role = useRoleStore((s) => s.role);
  const nav = useNav();
  const cases = useCaseStore((s) => s.cases);
  const upsert = useCaseStore((s) => s.upsert);

  useEffect(() => {
    if (Object.keys(useCaseStore.getState().cases).length === 0) {
      CASE_CARDS.forEach(upsert);
    }
  }, [upsert]);

  if (role !== 'manager') {
    return (
      <div className="flex h-[calc(100dvh-4rem)] items-center justify-center p-6">
        <p className="text-body2 text-muted">근로자 데이터 관리는 담당자 권한으로만 이용할 수 있습니다.</p>
      </div>
    );
  }

  const workers = Object.values(cases).filter((card) => card.workerRef);

  return (
    <section aria-label="근로자 데이터 관리" className="flex h-[calc(100dvh-4rem)] overflow-hidden bg-surface">
      <section className="flex min-w-0 flex-1 flex-col gap-4 overflow-y-auto p-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-heading2 font-bold text-ink">근로자</h1>
          <p className="text-caption1 text-subtle">
            E-9 · {workers.length}명 · 상태는 DB가 진실의 원천(RAG에 저장하지 않음)
          </p>
        </header>

        <div className="overflow-hidden rounded-in border border-hairline">
          <div className="grid grid-cols-[1fr_90px_90px_110px_70px_90px_120px] items-center gap-2 border-b border-hairline bg-surface px-3 py-2 text-pc-2xs font-bold text-subtle">
            <span>이름</span>
            <span>국적</span>
            <span>팀</span>
            <span>체류만료</span>
            <span>D-day</span>
            <span>서류 스캔</span>
            <span>최근 업데이트</span>
          </div>
          {workers.map((card) => {
            const sheet = CASE_SHEETS[card.caseId];
            const docsFraction = sheet?.docs
              ? `${sheet.docs.filter((d) => d.status === 'received').length}/${sheet.docs.length}`
              : '—';
            const lastUpdated = sheet?.activity[0]?.at ?? '—';
            return (
              <div
                key={card.caseId}
                className="grid grid-cols-[1fr_90px_90px_110px_70px_90px_120px] items-center gap-2 border-b border-hairline px-3 py-2.5 last:border-none"
              >
                <span className="truncate text-pc-sm font-semibold text-ink">{card.workerRef?.displayName}</span>
                <span className="text-pc-xs text-subtle">{card.workerRef?.nationality}</span>
                <span className="text-pc-xs text-subtle">{card.workerRef?.team}</span>
                <span className="text-pc-xs text-subtle">{card.stayExpiryDate ?? '—'}</span>
                <span className={`text-pc-xs font-bold tabular-nums ${dDayTextClass(card.dDay)}`}>
                  {card.dDay !== undefined ? dDayLabel(card.dDay) : '—'}
                </span>
                <span className="text-pc-xs tabular-nums text-faint">{docsFraction}</span>
                <span className="text-pc-2xs tabular-nums text-faint">{lastUpdated}</span>
              </div>
            );
          })}
        </div>
      </section>

      <aside aria-label="데이터 가져오기" className="flex w-[340px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-hairline bg-canvas p-4">
        <section className="flex flex-col gap-2.5 rounded-card bg-surface p-4">
          <div className="flex items-center gap-2.5">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-in bg-approvalbg">
              <IconDoc width={18} height={18} className="text-primary" />
            </span>
            <span className="text-label1 font-semibold text-ink">CSV 가져오기</span>
          </div>
          <p className="text-caption1 leading-relaxed text-muted">
            같은 파일을 다시 실행해도 중복 케이스가 생기지 않습니다.
          </p>
          <Button variant="outline" size="sm" onClick={() => nav.toCasesImport()}>
            CSV로 일괄 등록
          </Button>
        </section>

        <section className="flex flex-col gap-2.5 rounded-card border border-dashed border-line p-4">
          <span className="text-label1 font-semibold text-ink">서류 스캔 업로드</span>
          <p className="text-caption1 leading-relaxed text-muted">
            여권·계약서·증명서 파일을 끌어다 놓으면 근로자·서류 유형을 자동 분류해 확인 대기로
            올립니다.
          </p>
          <p className="text-caption1 text-faint">준비 중 — 이번 릴리스에는 포함되지 않습니다.</p>
        </section>

        <p className="mt-auto rounded-in bg-surface px-2.5 py-2 text-pc-2xs text-muted">
          개인정보는 DB에만 저장되고, LLM/RAG에 전달되지 않습니다.
        </p>
      </aside>
    </section>
  );
}
