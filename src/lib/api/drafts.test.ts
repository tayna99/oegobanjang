import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchCaseDraft, type DraftDto } from './drafts';

// SD-5 — lib/api/drafts.ts는 순수 fetch+DTO 변환만 한다(draft.py DraftOut을 그대로 매핑
// + 언어 라벨 부여). citations.test.ts와 동일 관례.
describe('lib/api/drafts', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  function makeDraftDto(overrides: Partial<DraftDto> = {}): DraftDto {
    return {
      draft_id: 'drf1',
      channel: 'Zalo',
      purpose: '서류 요청 메시지',
      status: 'draft',
      langs: [
        { lang: 'ko', text: '한국어 원문', is_revised: false },
        { lang: 'vi', text: '베트남어 원문', is_revised: false },
      ],
      ...overrides,
    };
  }

  it('fetchCaseDraft는 /api/v1/cases/{id}/draft를 호출하고 Draft로 변환한다(언어 라벨 매핑 포함)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(makeDraftDto()), { status: 200 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await fetchCaseDraft('cs1');

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/cases/cs1/draft'), expect.any(Object));
    expect(result).toEqual({
      draftId: 'drf1',
      channel: 'Zalo',
      purpose: '서류 요청 메시지',
      status: 'draft',
      langs: [
        { lang: 'ko', label: '한국어', text: '한국어 원문', isRevised: false },
        { lang: 'vi', label: '베트남어', text: '베트남어 원문', isRevised: false },
      ],
    });
  });

  it('is_revised 변형도 필터링 없이 그대로 노출한다(필터링은 화면 몫)', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(makeDraftDto({ langs: [{ lang: 'ko', text: '수정본', is_revised: true }] })), {
        status: 200,
      }),
    ) as unknown as typeof fetch;

    const result = await fetchCaseDraft('cs1');
    expect(result.langs).toEqual([{ lang: 'ko', label: '한국어', text: '수정본', isRevised: true }]);
  });

  it('알 수 없는 언어 코드는 코드 자체를 라벨로 폴백한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(makeDraftDto({ langs: [{ lang: 'th', text: '태국어 원문', is_revised: false }] })), {
        status: 200,
      }),
    ) as unknown as typeof fetch;

    const result = await fetchCaseDraft('cs1');
    expect(result.langs[0]).toEqual({ lang: 'th', label: 'th', text: '태국어 원문', isRevised: false });
  });

  it('비2xx 응답은 ApiError를 그대로 던진다', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '초안을 찾을 수 없습니다' }), { status: 404 })) as unknown as typeof fetch;

    await expect(fetchCaseDraft('cs_no_draft')).rejects.toMatchObject({ status: 404 });
  });
});
