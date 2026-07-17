import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchThreadDetail, fetchThreads } from './threads';
import type { MessageDto, ThreadDetailDto, ThreadDto } from './threads';

// R2.3 — lib/api/threads.ts는 순수 fetch+DTO 변환만 한다(요약/상세 매핑, 배지 파생은 lib/threads.ts 몫).
describe('lib/api/threads', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  const worker = { display_name: '응웬 반 아', nationality: '베트남', team: '제조1팀' };

  describe('fetchThreads', () => {
    it('message_count가 0이면 preview가 "아직 응답이 없습니다"이다', async () => {
      const dtos: ThreadDto[] = [
        { id: 't1', worker, channel: 'sms', last_message_at: null, message_count: 0, latest_interpretation_status: null },
      ];
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dtos), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreads();
      expect(result).toHaveLength(1);
      expect(result[0].messages).toEqual([]);
      expect(result[0].interpretationStatus).toBe('none');
      expect(result[0].preview).toBe('아직 응답이 없습니다');
    });

    it('message_count가 있으면 preview가 "메시지 N건"이다', async () => {
      const dtos: ThreadDto[] = [
        {
          id: 't1',
          worker,
          channel: 'sms',
          last_message_at: '2026-07-17T09:20:00Z',
          message_count: 3,
          latest_interpretation_status: null,
        },
        { id: 't2', worker, channel: 'zalo', last_message_at: null, message_count: 1, latest_interpretation_status: null },
      ];
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dtos), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreads();
      expect(result).toHaveLength(2);
      expect(result[0].messages).toEqual([]);
      expect(result[0].interpretationStatus).toBe('none');
      expect(result[0].preview).toBe('메시지 3건');
      expect(result[1].preview).toBe('메시지 1건');
    });

    // 코드리뷰 지적(PR #16 P1 재발): 목록 DTO가 latest_interpretation_status를 안 내려주던
    // 시절엔 toThreadSummary()가 무조건 'none'을 반환해, real API 모드에서 응답 도착 배지·
    // 정렬이 항상 죽어 있었다 — 목록 단계에서도 서버가 내려준 상태를 그대로 반영해야 한다.
    it('latest_interpretation_status가 proposed면 목록에서도 pending_review·응답 도착 문구다', async () => {
      const dtos: ThreadDto[] = [
        {
          id: 't1',
          worker,
          channel: 'sms',
          last_message_at: '2026-07-17T09:20:00Z',
          message_count: 2,
          latest_interpretation_status: 'proposed',
        },
      ];
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dtos), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreads();
      expect(result[0].interpretationStatus).toBe('pending_review');
      expect(result[0].preview).toBe('응답이 도착했습니다');
    });

    it('latest_interpretation_status가 confirmed면 목록에서도 confirmed·확인 완료 문구다', async () => {
      const dtos: ThreadDto[] = [
        {
          id: 't1',
          worker,
          channel: 'sms',
          last_message_at: '2026-07-17T09:20:00Z',
          message_count: 2,
          latest_interpretation_status: 'confirmed',
        },
      ];
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dtos), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreads();
      expect(result[0].interpretationStatus).toBe('confirmed');
      expect(result[0].preview).toBe('확인 완료');
    });
  });

  describe('fetchThreadDetail', () => {
    function baseMessage(overrides: Partial<MessageDto>): MessageDto {
      return {
        id: 'm1',
        direction: 'inbound',
        channel: 'sms',
        lang: 'vi',
        body_original: '원문',
        body_ko: '번역문',
        received_at: '2026-07-17T09:20:00Z',
        created_at: '2026-07-17T09:20:00Z',
        interpretation: null,
        ...overrides,
      };
    }

    it('direction inbound는 in으로, system은 out으로 사상한다', async () => {
      const dto: ThreadDetailDto = {
        id: 't1',
        worker,
        channel: 'sms',
        messages: [baseMessage({ id: 'm1', direction: 'inbound' }), baseMessage({ id: 'm2', direction: 'system' })],
      };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.messages[0].direction).toBe('in');
      expect(result.messages[1].direction).toBe('out');
    });

    it('body_ko가 있으면 body_ko를 사용한다', async () => {
      const dto: ThreadDetailDto = {
        id: 't1',
        worker,
        channel: 'sms',
        messages: [baseMessage({ body_ko: '번역문', body_original: '원문' })],
      };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.messages[0].body).toBe('번역문');
    });

    it('body_ko가 null이면 body_original로 대체한다', async () => {
      const dto: ThreadDetailDto = {
        id: 't1',
        worker,
        channel: 'sms',
        messages: [baseMessage({ body_ko: null, body_original: '원문' })],
      };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.messages[0].body).toBe('원문');
    });

    it('interpretation이 하나도 없으면 interpretationStatus는 none이다', async () => {
      const dto: ThreadDetailDto = {
        id: 't1',
        worker,
        channel: 'sms',
        messages: [baseMessage({ interpretation: null })],
      };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.interpretationStatus).toBe('none');
    });

    it('가장 나중의 interpretation이 proposed면 pending_review이다', async () => {
      const dto: ThreadDetailDto = {
        id: 't1',
        worker,
        channel: 'sms',
        messages: [
          baseMessage({
            id: 'm1',
            interpretation: { id: 'i1', summary_ko: '요약1', confidence: 'high', status: 'confirmed', confirmed_at: '2026-07-17T09:00:00Z' },
          }),
          baseMessage({
            id: 'm2',
            interpretation: { id: 'i2', summary_ko: '요약2', confidence: 'high', status: 'proposed', confirmed_at: null },
          }),
        ],
      };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.interpretationStatus).toBe('pending_review');
    });

    it('가장 나중의 interpretation이 confirmed면 confirmed이다', async () => {
      const dto: ThreadDetailDto = {
        id: 't1',
        worker,
        channel: 'sms',
        messages: [
          baseMessage({
            id: 'm1',
            interpretation: { id: 'i1', summary_ko: '요약1', confidence: 'high', status: 'proposed', confirmed_at: null },
          }),
          baseMessage({
            id: 'm2',
            interpretation: { id: 'i2', summary_ko: '요약2', confidence: 'high', status: 'confirmed', confirmed_at: '2026-07-17T09:10:00Z' },
          }),
        ],
      };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.interpretationStatus).toBe('confirmed');
    });

    it('중간 메시지가 아니라 마지막 interpretation 보유 메시지를 기준으로 삼는다', async () => {
      // m3는 interpretation이 없다 — reverse-find는 m2(proposed)를 찾아야 한다(m3의 null 무시).
      const dto: ThreadDetailDto = {
        id: 't1',
        worker,
        channel: 'sms',
        messages: [
          baseMessage({
            id: 'm1',
            interpretation: { id: 'i1', summary_ko: '요약1', confidence: 'high', status: 'confirmed', confirmed_at: '2026-07-17T09:00:00Z' },
          }),
          baseMessage({
            id: 'm2',
            interpretation: { id: 'i2', summary_ko: '요약2', confidence: 'high', status: 'proposed', confirmed_at: null },
          }),
          baseMessage({ id: 'm3', interpretation: null }),
        ],
      };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.interpretationStatus).toBe('pending_review');
    });

    it('worker가 null이면 알 수 없음 자리표시자로 채운다', async () => {
      const dto: ThreadDetailDto = { id: 't1', worker: null, channel: 'sms', messages: [baseMessage({})] };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.workerRef).toEqual({ displayName: '알 수 없음', nationality: '-', maskLevel: 'masked' });
    });

    it('알려진 채널 sms는 SMS로 라벨링된다', async () => {
      const dto: ThreadDetailDto = { id: 't1', worker, channel: 'sms', messages: [baseMessage({})] };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.channelLabel).toBe('SMS');
    });

    it('알려지지 않은 채널은 원문 그대로 라벨링된다', async () => {
      const dto: ThreadDetailDto = { id: 't1', worker, channel: 'kakao', messages: [baseMessage({ channel: 'kakao' })] };
      global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dto), { status: 200 })) as unknown as typeof fetch;

      const result = await fetchThreadDetail('t1');
      expect(result.channelLabel).toBe('kakao');
    });
  });
});
