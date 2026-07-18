import { useSessionStore } from '@/stores/sessionStore';
import { apiFetch } from './client';

// POST /api/v1/packages/{case_id}/link (발급/재발급) · GET /api/v1/packages/link/{link_token}
// (열람) 어댑터(R2.6) — backend/app/schemas/package.py의 PackageLinkStatus 그대로(snake_case).
// 패키지 문서 콘텐츠는 포함하지 않는다 — 프론트는 기존 mock 콘텐츠(mocks/packages.ts)를
// 그대로 렌더하고, 이 응답은 "링크가 살아있는가"만 쓴다.
//
// 코드리뷰 지적(PR #20 P1): GET을 case_id로 조회하던 이전 버전은 case_id(PK, 불변)를
// 비밀값으로 취급해 재발급으로도 유출된 링크를 회수할 수 없었다 — 이제 발급/재발급마다
// 새로 회전하는 link_token으로만 조회한다.
export interface PackageLinkStatusDto {
  case_id: string;
  link_token: string;
  issued_at: string;
  expires_at: string;
}

export interface PackageLinkStatus {
  caseId: string;
  linkToken: string;
  issuedAt: string;
  expiresAt: string;
}

function toStatus(dto: PackageLinkStatusDto): PackageLinkStatus {
  return { caseId: dto.case_id, linkToken: dto.link_token, issuedAt: dto.issued_at, expiresAt: dto.expires_at };
}

// 발급/재발급 — manager/owner 인증 필요(PackagePage "링크 재발급"). case_id로 요청하고,
// 응답의 linkToken이 실제 공개 URL(ROUTES.packageLink)을 구성하는 값이다.
export async function issuePackageLink(caseId: string): Promise<PackageLinkStatus> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<PackageLinkStatusDto>(`/api/v1/packages/${caseId}/link`, {
    method: 'POST',
    token,
  });
  return toStatus(dto);
}

// 무인증 — ExpertLinkPage(로그인 없는 최상위 라우트)가 URL의 link_token으로 호출한다.
// 404(ApiError)는 "링크 없음/만료"를 뜻한다 — 호출부가 잡아서 안내 화면으로 렌더한다
// (서버 강제, R2.6 핵심). 응답의 caseId로 mock 콘텐츠(mocks/packages.ts)를 찾는다.
export async function fetchPackageLink(linkToken: string): Promise<PackageLinkStatus> {
  const dto = await apiFetch<PackageLinkStatusDto>(`/api/v1/packages/link/${linkToken}`);
  return toStatus(dto);
}
