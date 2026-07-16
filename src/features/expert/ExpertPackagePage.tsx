import { useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { isLinkExpired } from '@/lib/packageLink';
import { useNav } from '@/lib/nav';
import { expertAccountFor, tenantFor } from '@/mocks/expert';
import { packageFor } from '@/mocks/packages';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { DocumentPreview } from '@/features/packagePkg/PackagePage';
import { StructuredReplyForm } from '@/features/packagePkg/StructuredReplyForm';
import { ExpertBrandHeader } from './ExpertBrandHeader';

// 화이트라벨 패키지 뷰(7-1) — 개인 대시보드에서 진입. 콘텐츠(DocumentPreview·구조화된 회신)는
// 무인증 링크 뷰(ExpertLinkPage)와 동일하되, 외고반장 대신 행정사 브랜드 헤더 + "대시보드로"
// 뒤로가기 + 소속 회사(tenant)명을 얹는다. 이 패키지가 이 expert의 것이 아니면(recipient 불일치)
// tenant scope 밖 — 스펙 §1 "scope 밖은 404(존재 비노출)" 원칙대로 링크 없음 안내만.
export function ExpertPackagePage() {
  const { expertId, packageId } = useParams<{ expertId: string; packageId: string }>();
  const nav = useNav();
  const account = expertAccountFor(expertId);
  const pkg = packageFor(packageId);
  const events = useEvidenceStore((s) => s.events);
  const appendEvidence = useEvidenceStore((s) => s.append);
  const logged = useRef(false);

  // scope 검사 — 계정이 없거나, 패키지가 없거나, 그 패키지 수신자가 이 행정사가 아니면 노출하지 않는다.
  const inScope = Boolean(account && pkg && pkg.recipient === account.officeName);
  const expired = inScope && pkg ? isLinkExpired(pkg, events) : false;

  useEffect(() => {
    if (!inScope || !pkg || expired || logged.current) return;
    logged.current = true;
    appendEvidence({
      id: `${pkg.packageId}-link-viewed-${Date.now()}`,
      type: 'package_link_viewed',
      at: new Date().toISOString(),
      caseId: pkg.packageId,
      summary: `행정사가 패키지 링크 열람 · ${pkg.recipient}`,
      actor: pkg.recipient,
    });
  }, [inScope, pkg, expired, appendEvidence]);

  if (!account || !expertId || !pkg || !inScope) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas p-5">
        <p className="text-body2 text-muted">링크를 찾을 수 없습니다.</p>
      </div>
    );
  }

  if (expired) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col gap-5 bg-canvas px-5 py-8">
        <ExpertBrandHeader account={account} onBack={() => nav.toExpertDashboard(expertId)} />
        <div className="rounded-in bg-approvalbg px-5 py-4 text-center">
          <p className="text-label1 font-semibold text-approval">링크가 만료되었습니다</p>
          <p className="mt-1 text-caption1 leading-relaxed text-approval">
            보안을 위해 만료형 링크로만 전달됩니다. 담당자에게 재발급을 요청해주세요.
          </p>
        </div>
      </div>
    );
  }

  const tenant = tenantFor(pkg.tenantId);
  const on = new Set(pkg.items.filter((item) => item.defaultOn).map((item) => item.key));

  return (
    <div className="mx-auto flex min-h-dvh max-w-screen-md flex-col gap-5 bg-canvas px-5 py-8">
      <ExpertBrandHeader
        account={account}
        subtitle={tenant ? `${tenant.name} · 검토 요청` : '검토 요청'}
        onBack={() => nav.toExpertDashboard(expertId)}
      />
      <DocumentPreview pkg={pkg} on={on} />
      <StructuredReplyForm packageId={pkg.packageId} recipient={pkg.recipient} />
    </div>
  );
}
