// 행정사 무인증 링크 뷰(7단계 §1·§4) — Shell(로그인 앱 챙) 바깥의 최상위 라우트. 로그인 없이
// 만료형 링크로 접근하는 유일한 화면이라 PackagePage와 같은 콘텐츠(DocumentPreview)를 그대로
// 재사용하되 nav/tabbar 없이 렌더한다. 이미 얼어붙은 채택 디자인(PC §2d)의 콘텐츠 확장이지
// 새 시각 요소가 아니다 — system-derived 태깅 대상 아님(콘텐츠 자체는 목업 있음).
//
// 구조화된 회신(PC 4e 확장, 2026-07-13) — reference/design-system/외고반장 PC_4a-4f(신규티어)
// .dc.html §4e 이식. 회신은 evidence(package_reply)로 기록된다 — M8 전역 판단 기록
// (GlobalEvidencePage)에서 항상 확인 가능하고, R0.5(2026-07-17)부터는 케이스 상세의
// "케이스 타임라인"(CaseWorkbench.CaseTimeline, lib/audit.ts caseTimelineActivity)에도
// 실시간으로 반영된다.
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiError } from '@/lib/api/client';
import { API_MODE } from '@/lib/api/config';
import { fetchPackageLink } from '@/lib/api/packages';
import { isLinkExpired } from '@/lib/packageLink';
import { packageFor } from '@/mocks/packages';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { DocumentPreview } from './PackagePage';
import { StructuredReplyForm } from './StructuredReplyForm';

export function ExpertLinkPage() {
  const { packageId } = useParams<{ packageId: string }>();
  const pkg = packageFor(packageId);
  const events = useEvidenceStore((s) => s.events);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const logged = useRef(false);

  // real 모드 — 만료·열람 로그를 서버가 강제한다(R2.6, "클라이언트 가드 → 404"). GET 성공
  // 자체가 곧 열람 기록이다(services/packages.py가 같은 트랜잭션에서 evidence를 남긴다) —
  // 프론트가 별도로 package_link_viewed를 재전송하지 않는다.
  const [realLinkValid, setRealLinkValid] = useState<boolean | null>(null);
  useEffect(() => {
    // pkg가 없으면(mocks/packages.ts에 없는 packageId) 콘텐츠 자체가 없을 게 확정이라
    // 서버까지 왕복하지 않는다 — 아래 !pkg 분기가 어차피 먼저 "찾을 수 없음"을 렌더한다.
    if (API_MODE !== 'real' || !packageId || !pkg) return;
    let cancelled = false;
    fetchPackageLink(packageId)
      .then(() => {
        if (!cancelled) setRealLinkValid(true);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setRealLinkValid(false);
        else console.error('[ExpertLinkPage] 링크 확인 실패', err);
      });
    return () => {
      cancelled = true;
    };
  }, [packageId, pkg]);

  const mockExpired = pkg ? isLinkExpired(pkg, events) : false;
  const expired = API_MODE === 'real' ? realLinkValid === false : mockExpired;

  // mock 모드만 클라이언트에서 열람 evidence를 남긴다(기존 동작 그대로). real 모드는 위
  // GET이 이미 서버에 남겼으므로 다시 appendEvidence하지 않는다 — useRef 가드는 StrictMode
  // 이중 호출 방지용(CaseReviewPage의 review_started와 동일 관례, 단 여기선 "이미 있는
  // id면 스킵"이 아니라 "이 마운트에서 한 번만" — 재방문마다 새 로그가 남아야 한다).
  useEffect(() => {
    if (API_MODE === 'real' || !pkg || expired || logged.current) return;
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

  if (API_MODE === 'real' && realLinkValid === null) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <p className="text-body2 text-muted">링크 확인 중…</p>
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
