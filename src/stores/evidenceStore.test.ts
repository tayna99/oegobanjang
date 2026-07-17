import { afterEach, describe, expect, it, vi } from 'vitest';
import { useEvidenceStore } from './evidenceStore';
import type { EvidenceEvent } from '@/types';

// mock 모드(기본 API_MODE) — 서버 기록 분기는 evidenceStore.realApi.test.ts가 다룬다.
describe('evidenceStore — mock 모드', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useEvidenceStore.getState().reset();
    global.fetch = originalFetch;
  });

  function makeEvent(overrides: Partial<EvidenceEvent> = {}): EvidenceEvent {
    return { id: 'e1', type: 'role_granted', at: '2026-07-17T09:00:00Z', summary: '역할 부여', ...overrides };
  }

  it('append는 이벤트를 추가하고 동결한다', () => {
    useEvidenceStore.getState().append(makeEvent());
    const [event] = useEvidenceStore.getState().events;
    expect(event.id).toBe('e1');
    expect(Object.isFrozen(event)).toBe(true);
  });

  it('같은 id를 다시 append하면 no-op이다(append-only 중복 방지)', () => {
    useEvidenceStore.getState().append(makeEvent());
    useEvidenceStore.getState().append(makeEvent({ summary: '다른 요약' }));
    expect(useEvidenceStore.getState().events).toHaveLength(1);
    expect(useEvidenceStore.getState().events[0].summary).toBe('역할 부여');
  });

  it('mock 모드는 append 시 서버로 아무 것도 보내지 않는다', () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;
    useEvidenceStore.getState().append(makeEvent());
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('hydrate는 없는 id만 추가하고 기존 이벤트를 덮어쓰지 않는다', () => {
    useEvidenceStore.getState().append(makeEvent({ summary: '원본' }));
    useEvidenceStore.getState().hydrate([makeEvent({ summary: '서버가 준 값' }), makeEvent({ id: 'e2' })]);
    const events = useEvidenceStore.getState().events;
    expect(events).toHaveLength(2);
    expect(events.find((e) => e.id === 'e1')?.summary).toBe('원본');
  });

  it('reset은 이벤트를 전부 비운다', () => {
    useEvidenceStore.getState().append(makeEvent());
    useEvidenceStore.getState().reset();
    expect(useEvidenceStore.getState().events).toHaveLength(0);
  });
});
