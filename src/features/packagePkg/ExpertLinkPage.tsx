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
import { useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
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
