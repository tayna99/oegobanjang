import { afterEach, describe, expect, it, vi } from 'vitest';
import { createEvidenceEvent, fetchEvidence, toEvidenceEvent, type EvidenceEventDto } from './evidence';

// R2.5 — lib/api/evidence.ts는 순수 fetch+DTO 변환만 한다(schemas/evidence.py EvidenceEventOut을
// 그대로 매핑, docs/DB_SCHEMA.md §8 계약: hash=input_hash, evidenceRef='#'+event_no, actor=actor_display).
describe('lib/api/evidence', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  function makeDto(overrides: Partial<EvidenceEventDto> = {}): EvidenceEventDto {
    return {
      id: 'evt_1',
      company_id: 'cmp1',
      event_no: 4790,
      type: 'interpretation_confirmed',
      at: '2026-07-17T09:00:00Z',
      case_id: 'nguyen',
      summary: '해석 확인',
      input_hash: 'sha256:aaaa',
      actor_display: '김담당',
      ...overrides,
    };
  }

  describe('toEvidenceEvent', () => {
    it('DTO를 프론트 EvidenceEvent 계약대로 매핑한다', () => {
      const event = toEvidenceEvent(makeDto());
      expect(event).toEqual({
        id: 'evt_1',
        type: 'interpretation_confirmed',
        at: '2026-07-17T09:00:00Z',
        caseId: 'nguyen',
        hash: 'sha256:aaaa',
        summary: '해석 확인',
        actor: '김담당',
        evidenceRef: '#4790',
      });
    });

    it('case_id/actor_display/input_hash가 null이면 undefined로 비운다', () => {
      const event = toEvidenceEvent(makeDto({ case_id: null, actor_display: null, input_hash: null }));
      expect(event.caseId).toBeUndefined();
      expect(event.actor).toBeUndefined();
      expect(event.hash).toBeUndefined();
    });
  });

  describe('createEvidenceEvent', () => {
    it('POST /api/v1/evidence를 호출한다(action_id/approval_id/run_id 없이 case_id·summary만)', async () => {
      const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(makeDto()), { status: 201 }));
      global.fetch = mockFetch as unknown as typeof fetch;

      await createEvidenceEvent({ type: 'role_granted', caseId: 'nguyen', summary: '역할 부여' });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/evidence',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ type: 'role_granted', case_id: 'nguyen', summary: '역할 부여' }),
        }),
      );
    });

    it('caseId가 없으면 case_id: null로 보낸다(회사 단위 이벤트)', async () => {
      const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(makeDto()), { status: 201 }));
      global.fetch = mockFetch as unknown as typeof fetch;

      await createEvidenceEvent({ type: 'role_granted', summary: '역할 부여' });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/evidence',
        expect.objectContaining({ body: JSON.stringify({ type: 'role_granted', case_id: null, summary: '역할 부여' }) }),
      );
    });
  });

  describe('fetchEvidence', () => {
    it('GET /api/v1/evidence를 호출하고 EvidenceEvent[]로 변환한다', async () => {
      const dtos = [makeDto(), makeDto({ id: 'evt_2', event_no: 4791, type: 'role_granted', case_id: null })];
      const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dtos), { status: 200 }));
      global.fetch = mockFetch as unknown as typeof fetch;

      const result = await fetchEvidence();

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/evidence', expect.anything());
      expect(result).toHaveLength(2);
      expect(result[1].evidenceRef).toBe('#4791');
    });
  });
});
