import { useSessionStore } from '@/stores/sessionStore';
import { apiFetch } from './client';

// POST/GET /api/v1/packages/{case_id}/link 어댑터(R2.6) — backend/app/schemas/package.py의
// PackageLinkStatus 그대로(snake_case). 패키지 문서 콘텐츠는 포함하지 않는다 — 프론트는
// 기존 mock 콘텐츠(mocks/packages.ts)를 그대로 렌더하고, 이 응답은 "링크가 살아있는가"만 쓴다.
export interface PackageLinkStatusDto {
  case_id: string;
  issued_at: string;
  expires_at: string;
}

export interface PackageLinkStatus {
  caseId: string;
  issuedAt: string;
  expiresAt: string;
}

function toStatus(dto: PackageLinkStatusDto): PackageLinkStatus {
  return { caseId: dto.case_id, issuedAt: dto.issued_at, expiresAt: dto.expires_at };
}

// 발급/재발급 — manager/owner 인증 필요(PackagePage "링크 재발급").
export async function issuePackageLink(caseId: string): Promise<PackageLinkStatus> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<PackageLinkStatusDto>(`/api/v1/packages/${caseId}/link`, {
    method: 'POST',
    token,
  });
  return toStatus(dto);
}

// 무인증 — ExpertLinkPage(로그인 없는 최상위 라우트)가 호출한다. 404(ApiError)는 "링크
// 없음/만료"를 뜻한다 — 호출부가 잡아서 안내 화면으로 렌더한다(서버 강제, R2.6 핵심).
export async function fetchPackageLink(caseId: string): Promise<PackageLinkStatus> {
  const dto = await apiFetch<PackageLinkStatusDto>(`/api/v1/packages/${caseId}/link`);
  return toStatus(dto);
}
