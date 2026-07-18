import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchPackageLink, issuePackageLink, type PackageLinkStatusDto } from './packages';
import { ApiError } from './client';

// R2.6 — lib/api/packages.ts는 순수 fetch+DTO 변환만 한다(schemas/package.py PackageLinkStatus를
// 그대로 매핑). fetchPackageLink는 무인증(토큰 없이 호출)이라는 점이 다른 어댑터와 다르다.
//
// 코드리뷰 지적(PR #20 P1): case_id를 공개 링크의 비밀값으로 쓰면 재발급으로도 유출된
// 링크를 회수할 수 없었다 — 이제 발급/재발급마다 회전하는 link_token이 실제 조회 키다
// (GET은 /api/v1/packages/link/{link_token}, case_id 경로가 아니다).
describe('lib/api/packages', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  const dto: PackageLinkStatusDto = {
    case_id: 'cs_batbayar',
    link_token: 'tok_abc123',
    issued_at: '2026-07-17T09:00:00Z',
    expires_at: '2026-07-24T09:00:00Z',
  };

  it('issuePackageLink는 POST /api/v1/packages/{caseId}/link를 호출하고 linkToken을 반환한다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 201 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await issuePackageLink('cs_batbayar');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/packages/cs_batbayar/link',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result).toEqual({
      caseId: 'cs_batbayar',
      linkToken: 'tok_abc123',
      issuedAt: dto.issued_at,
      expiresAt: dto.expires_at,
    });
  });

  it('fetchPackageLink는 GET /api/v1/packages/link/{linkToken}를 호출하고 Authorization 헤더가 없다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await fetchPackageLink('tok_abc123');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/packages/link/tok_abc123',
      expect.anything(),
    );
    const headers = mockFetch.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
    expect(result.caseId).toBe('cs_batbayar');
  });

  it('링크가 만료·미발급이면 404 ApiError를 던진다', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '링크를 찾을 수 없습니다' }), { status: 404 })) as unknown as typeof fetch;

    await expect(fetchPackageLink('no-such-token')).rejects.toBeInstanceOf(ApiError);
  });
});
