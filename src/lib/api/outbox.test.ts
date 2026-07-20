import { afterEach, describe, expect, it, vi } from 'vitest';
import { executeDispatch } from './outbox';

// R3 stage ② — lib/api/outbox.ts는 순수 fetch+DTO 매핑만 한다(schemas/outbox.py OutboxOut을
// 그대로 반영). DispatchQueuePage의 real-mode "발송 실행"이 이 함수를 fire-and-forget으로 부른다.
describe('lib/api/outbox', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('executeDispatch는 POST /api/v1/outbox를 action_id와 함께 호출한다', async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ id: 'ob_1', channel: 'sms', status: 'sent', external_id: 'stub:sms:abc' }),
        { status: 201 },
      ),
    );
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await executeDispatch('act1');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/outbox',
      expect.objectContaining({ method: 'POST' }),
    );
    const body = JSON.parse(mockFetch.mock.calls[0][1]?.body as string);
    expect(body).toEqual({ action_id: 'act1' });
    expect(result.status).toBe('sent');
    expect(result.external_id).toBe('stub:sms:abc');
  });

  it('실패 응답이면 예외를 던진다(호출부가 fire-and-forget으로 catch한다)', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '승인이 없습니다' }), { status: 403 })) as unknown as typeof fetch;

    await expect(executeDispatch('act-not-approved')).rejects.toThrow();
  });
});
