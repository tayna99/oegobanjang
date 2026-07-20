import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchCitationLibrary, type CitationDto } from './citations';

// SD-3 — lib/api/citations.ts는 순수 fetch+DTO 변환만 한다(citation.py CitationOut을 그대로 매핑).
describe('lib/api/citations', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  function makeCitationDto(overrides: Partial<CitationDto> = {}): CitationDto {
    return {
      id: 'cit_001',
      grade: 'A',
      title: '출입국관리법 시행규칙 · 연장 제출서류 별표',
      source: '국가법령정보센터',
      status: 'official',
      updated_at: '2026-07-01T00:00:00Z',
      ...overrides,
    };
  }

  it('fetchCitationLibrary는 company_id 쿼리로 /api/v1/citations를 호출하고 CitationRecord[]로 변환한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify([makeCitationDto()]), { status: 200 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await fetchCitationLibrary('cmp_greenfood');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/citations?company_id=cmp_greenfood'),
      expect.any(Object),
    );
    expect(result).toEqual([
      { id: 'cit_001', grade: 'A', title: '출입국관리법 시행규칙 · 연장 제출서류 별표', source: '국가법령정보센터', status: 'official', updatedAt: '2026-07-01T00:00:00Z' },
    ]);
  });

  it('빈 응답은 빈 배열로 변환된다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 })) as unknown as typeof fetch;

    const result = await fetchCitationLibrary('cmp_greenfood');

    expect(result).toEqual([]);
  });

  it('비2xx 응답은 ApiError를 그대로 던진다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: '접근 권한 없음' }), { status: 403 })) as unknown as typeof fetch;

    await expect(fetchCitationLibrary('cmp_greenfood')).rejects.toMatchObject({ status: 403 });
  });
});
