import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchLatestBriefing } from './briefings';
import type { CaseDto } from './cases';

// R2.x — briefings.ts는 404를 "브리핑 없음"으로 흡수하고, 그 외 비2xx는 그대로 던져야 한다.
describe('fetchLatestBriefing', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  const caseDto: CaseDto = {
    id: 'case1',
    case_code: 'C-001',
    title: '체류 만료 임박',
    severity: 'high',
    state: 'open',
    agent_stage: null,
    due_date: null,
    approval_required: false,
    prepared_by: 'agent',
    prepared_run_id: null,
    worker: null,
    primary_action: null,
    secondary_action: null,
  };

  it('200 응답을 snake_case에서 camelCase로 변환하고 cases를 toCaseCard로 매핑한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'brief1',
          briefing_date: '2026-07-17',
          generated_at: '2026-07-17T09:00:00Z',
          cases: [caseDto],
        }),
        { status: 200 },
      ),
    ) as unknown as typeof fetch;

    const result = await fetchLatestBriefing();

    expect(result?.briefingId).toBe('brief1');
    expect(result?.briefingDate).toBe('2026-07-17');
    expect(result?.generatedAt).toBe('2026-07-17T09:00:00Z');
    expect(result?.cases).toHaveLength(1);
    expect(result?.cases[0]?.caseId).toBe('case1');
  });

  it('404는 예외를 던지지 않고 null로 처리한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: '아직 브리핑 없음' }), { status: 404 })) as unknown as typeof fetch;

    const result = await fetchLatestBriefing();
    expect(result).toBeNull();
  });

  it('404가 아닌 비2xx 응답은 ApiError를 그대로 던진다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: '서버 오류' }), { status: 500 })) as unknown as typeof fetch;

    await expect(fetchLatestBriefing()).rejects.toMatchObject({ status: 500 });
  });
});
