import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { cn } from '@/lib/cn';
import { useNav } from '@/lib/nav';
import { isLinkExpired, LINK_VALIDITY_DAYS } from '@/lib/packageLink';
import {
  PACKAGE_EXPORT_FOOTER,
  PACKAGE_WATERMARK,
  packageFor,
  type HandoffPackage,
} from '@/mocks/packages';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';
import type { EvidenceEvent } from '@/types';

// 행정사 검토 패키지(관제형 §2d) — 포함 항목 토글 · 검토 요청서 미리보기 · 근거 각주 · 내보내기 이력(2.4).
// 내보내기는 승인 전 잠금(고정 가드레일). PII는 마스킹 값만(원문 없음). 데스크톱 3열/모바일 스택 반응형.

// 섹션 heading → 포함 항목 key (해제 시 문서에서 제외).
const SECTION_ITEM: Record<string, string> = {
  '1. 케이스 개요': 'summary',
  '2. 누락 서류': 'missing',
  // '3. 요청 사항'은 핵심이라 항상 포함(토글 없음).
};

function exportActionId(pkg: HandoffPackage) {
  return `${pkg.packageId}-handoff-export`;
}

function IncludeChecklist({
  pkg,
  on,
  toggle,
}: {
  pkg: HandoffPackage;
  on: Set<string>;
  toggle: (key: string) => void;
}) {
  return (
    <aside aria-label="포함 항목" className="flex w-full shrink-0 flex-col gap-2 lg:w-[290px]">
      <h2 className="text-caption1 font-bold tracking-wide text-muted">포함 항목</h2>
      <ul className="overflow-hidden rounded-in border border-hairline">
        {pkg.items.map((item) => (
          <li key={item.key} className="border-b border-hairline last:border-none">
            <label className="flex min-h-12 cursor-pointer items-center gap-2.5 px-3 py-2.5">
              <input type="checkbox" checked={on.has(item.key)} onChange={() => toggle(item.key)} className="size-4 accent-primary" />
              <span className="text-label1 text-ink">{item.label}</span>
              {item.note && <span className="text-caption1 text-dim">{item.note}</span>}
            </label>
          </li>
        ))}
      </ul>
      <p className="text-caption1 leading-relaxed text-subtle">
        항목 해제 시 패키지에서 제외됩니다. 원문 PII는 어떤 항목에도 포함되지 않습니다.
      </p>
    </aside>
  );
}

// ExpertLinkPage(행정사 무인증 뷰)가 그대로 재사용 — 새 시각 요소 없이 콘텐츠만 공유.
export function DocumentPreview({ pkg, on }: { pkg: HandoffPackage; on: Set<string> }) {
  const workerOn = on.has('worker');
  return (
    <section aria-label="검토 요청서" className="flex min-w-0 flex-1 flex-col gap-3">
      <p className="rounded-in bg-warnbg px-3.5 py-2 text-center text-caption1 font-semibold text-warning">{PACKAGE_WATERMARK}</p>
      <article className="mx-auto flex w-full max-w-[620px] flex-col gap-4 rounded-card border border-hairline bg-canvas p-6">
        <h2 className="text-heading2 font-bold text-ink">행정사 검토 요청서</h2>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-caption1">
          {[
            ['수신', pkg.recipient],
            ['발신', pkg.senderLine],
            ['작성일', pkg.createdAt],
            ['판단 기록', pkg.recordRef],
          ].map(([label, value]) => (
            <div key={label} className="flex gap-1.5">
              <dt className="text-subtle">{label}</dt>
              <dd className="min-w-0 truncate text-ink">{value}</dd>
            </div>
          ))}
        </dl>

        {pkg.sections.map((section) => {
          const gate = SECTION_ITEM[section.heading];
          if (gate && !on.has(gate)) return null;
          const lines = section.heading.startsWith('1.') && !workerOn
            ? section.lines.filter((l) => !l.startsWith('근로자') && !l.startsWith('외국인등록번호'))
            : section.lines;
          return (
            <div key={section.heading} className="flex flex-col gap-1">
              <h3 className="text-label1 font-bold text-ink">{section.heading}</h3>
              {lines.map((line) => (
                <p key={line} className="text-label1 leading-relaxed text-muted">{line}</p>
              ))}
            </div>
          );
        })}

        {on.has('history') && (
          <div className="flex flex-col gap-1">
            <h3 className="text-label1 font-bold text-ink">4. 이전 승인 이력 요약</h3>
            <p className="text-label1 leading-relaxed text-muted">· 06/12 1차 서류요청 승인 (판단 기록 #4712)</p>
          </div>
        )}

        <div className="flex flex-col gap-1 border-t border-hairline pt-3">
          <h3 className="text-caption1 font-bold text-subtle">근거</h3>
          {pkg.citations.map((c) => (
            <p key={c.id ?? c.title} className="text-caption1 text-muted">
              [{c.grade}] {c.title} {c.id ? `(${c.id})` : ''}
            </p>
          ))}
        </div>
      </article>
    </section>
  );
}

function EvidenceRail({
  pkg,
  approved,
  viewLog,
}: {
  pkg: HandoffPackage;
  approved: boolean;
  viewLog: EvidenceEvent[];
}) {
  return (
    <aside aria-label="근거·내보내기 레일" className="flex w-full shrink-0 flex-col gap-4 lg:w-[300px]">
      <section className="flex flex-col gap-2">
        <h2 className="text-caption1 font-bold tracking-wide text-muted">근거 문서 ({pkg.citations.length})</h2>
        <ul className="flex flex-col gap-1.5">
          {pkg.citations.map((c) => (
            <li key={c.id ?? c.title} className="flex items-center gap-2 rounded-in border border-hairline px-2.5 py-2">
              <span aria-hidden="true" className="flex size-[18px] shrink-0 items-center justify-center rounded bg-approvalbg text-pc-2xs font-bold text-approval">
                {c.grade}
              </span>
              <span className="min-w-0 flex-1 truncate text-pc-xs text-ink">{c.title}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-caption1 font-bold tracking-wide text-muted">내보내기 이력</h2>
        <ul className="flex flex-col gap-1.5">
          {pkg.exportHistory.map((e) => (
            <li key={e.ref} className="flex flex-col gap-0.5 rounded-in border border-hairline px-2.5 py-2">
              <span className="text-caption1 text-ink">
                {e.at} · {e.kind} · {e.actor}
              </span>
              <span className="font-mono text-pc-2xs text-dim">
                {e.ref} · {e.hash}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* 행정사 링크 열람 로그(7단계 §4) — package_link_viewed evidence. */}
      <section aria-label="링크 열람 이력" className="flex flex-col gap-2">
        <h2 className="text-caption1 font-bold tracking-wide text-muted">링크 열람 이력 ({viewLog.length})</h2>
        {viewLog.length === 0 ? (
          <p className="text-caption1 text-dim">아직 행정사가 링크를 열람하지 않았습니다.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {viewLog.map((e) => (
              <li key={e.id} className="rounded-in border border-hairline px-2.5 py-2 text-caption1 text-ink">
                {e.summary}
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className={cn('mt-auto rounded-in px-3 py-2.5 text-caption1', approved ? 'bg-succbg text-success' : 'bg-surface text-subtle')}>
        {approved ? '승인 완료 — 전달 준비 상태입니다.' : PACKAGE_EXPORT_FOOTER}
      </p>
    </aside>
  );
}

export function PackagePage() {
  const { packageId } = useParams<{ packageId: string }>();
  const nav = useNav();
  const pkg = packageFor(packageId);
  const role = useRoleStore((s) => s.role);
  const approvals = useApprovalStore((s) => s.approvals);
  const requestApproval = useApprovalStore((s) => s.requestApproval);
  const events = useEvidenceStore((s) => s.events);
  const appendEvidence = useEvidenceStore((s) => s.append);

  const [on, setOn] = useState<Set<string>>(() => new Set(pkg?.items.filter((i) => i.defaultOn).map((i) => i.key)));
  const [requested, setRequested] = useState(false);
  const [exported, setExported] = useState(false);

  useEffect(() => {
    if (pkg) setOn(new Set(pkg.items.filter((i) => i.defaultOn).map((i) => i.key)));
  }, [pkg]);

  const expired = useMemo(() => (pkg ? isLinkExpired(pkg, events) : false), [pkg, events]);
  const viewLog = useMemo(
    () => (pkg ? events.filter((e) => e.type === 'package_link_viewed' && e.caseId === pkg.packageId) : []),
    [pkg, events],
  );

  const approved = useMemo(
    () => (pkg ? approvals[exportActionId(pkg)]?.status === 'approved' : false),
    [approvals, pkg],
  );

  if (!pkg) {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">패키지를 찾을 수 없습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toHome()}>
          오늘 브리핑으로
        </Button>
      </div>
    );
  }

  const toggle = (key: string) =>
    setOn((cur) => {
      const next = new Set(cur);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const onRequestApproval = () => {
    const actionId = exportActionId(pkg);
    if (!approvals[actionId]) requestApproval(actionId);
    appendEvidence({
      id: `${actionId}-requested`,
      type: 'approval_requested',
      at: new Date().toISOString(),
      caseId: pkg.packageId,
      actionId,
      summary: `${pkg.workerName} · 행정사 패키지 전달 승인 요청 생성`,
      actor: 'system',
    });
    setRequested(true);
  };

  // 승인 후 "내보내기" — 실제 전달/제출은 하지 않는다(GOTCHAS: 전달 준비까지만).
  // 감사 로그에 exported 이벤트만 남긴다(evidence.ts의 batbayar-export-0031과 동일 패턴).
  const onExport = () => {
    appendEvidence({
      id: `${pkg.packageId}-handoff-exported`,
      type: 'exported',
      at: new Date().toISOString(),
      caseId: pkg.packageId,
      summary: `${pkg.workerName} · 행정사 패키지 PDF 내보내기`,
      actor: '김담당',
    });
    setExported(true);
  };

  // 링크 재발급(7단계 §4 "재발급은 manager") — 만료 여부 계산을 다시 유효로 되돌린다.
  const onReissue = () => {
    appendEvidence({
      id: `${pkg.packageId}-link-reissued-${Date.now()}`,
      type: 'package_link_issued',
      at: new Date().toISOString(),
      caseId: pkg.packageId,
      summary: `${pkg.workerName} · 행정사 패키지 링크 재발급`,
      actor: '김담당',
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-screen-2xl flex-col gap-4 px-5 pb-16 pt-5">
      <header className="flex flex-col gap-2">
        <span className="text-caption1 text-subtle">{pkg.eyebrow}</span>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-heading1 font-bold text-ink">행정사 검토 패키지</h1>
            <Chip tone="critical">{pkg.severityLabel}</Chip>
            <Chip tone="approval">{pkg.statusLabel}</Chip>
          </div>
          <div className="flex shrink-0 gap-2">
            {/* 링크 재발급 — manager 전용(7단계 §4). */}
            {role === 'manager' && (
              <Button variant="outline" size="sm" onClick={onReissue}>
                링크 재발급
              </Button>
            )}
            <Button variant="outline" size="sm" disabled={!approved || exported} onClick={onExport}>
              {exported ? '내보내기 완료' : approved ? '내보내기' : '내보내기 (승인 필요)'}
            </Button>
            <Button variant="primary" size="sm" disabled={requested} onClick={onRequestApproval}>
              {requested ? '승인 요청됨' : '승인 요청'}
            </Button>
          </div>
        </div>
        {/* 링크 만료 안내(7단계 §4 "만료형(기본 7일)") — 내부 관리 화면에서도 상태를 보여준다. */}
        {expired && (
          <p className="rounded-in bg-approvalbg px-3.5 py-3 text-body2 leading-relaxed text-approval">
            행정사 링크가 만료되었습니다({LINK_VALIDITY_DAYS}일 경과) — 재발급이 필요합니다.
          </p>
        )}
      </header>

      <div className="flex flex-col gap-5 lg:flex-row">
        <IncludeChecklist pkg={pkg} on={on} toggle={toggle} />
        <DocumentPreview pkg={pkg} on={on} />
        <EvidenceRail pkg={pkg} approved={approved} viewLog={viewLog} />
      </div>
    </div>
  );
}
