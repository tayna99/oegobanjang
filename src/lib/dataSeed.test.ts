import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSeedBriefing, useSeedCases, useSeedCitations, useSeedNotifications, useSeedThreads } from './dataSeed';
import { CASE_CARDS } from '@/mocks/fixtures';
import { CITATION_LIBRARY } from '@/mocks/citations';
import { THREADS } from '@/mocks/threads';
import { useBriefingStore } from '@/stores/briefingStore';
import { useCaseStore } from '@/stores/caseStore';
import { useCitationStore } from '@/stores/citationStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { useThreadStore } from '@/stores/threadStore';

// API_MODE 기본값('mock') 경로 — 실 API 모드는 dataSeed.realApi.test.ts에서 별도로 다룬다
// (모듈 목 vi.mock('./api/config')이 파일 전체에 호이스트되므로 같은 파일에서 두 값을
// 동시에 검증할 수 없다 — StepPhoneAuth.realApi.test.tsx와 동일한 분리 관례).
describe('useSeedCases / useSeedThreads — mock 모드', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useThreadStore.getState().reset();
  });

  it('caseStore가 비어있으면 CASE_CARDS로 시드한다', () => {
    renderHook(() => useSeedCases());
    expect(Object.keys(useCaseStore.getState().cases)).toHaveLength(CASE_CARDS.length);
  });

  it('caseStore에 이미 데이터가 있으면 다시 시드하지 않는다', () => {
    useCaseStore.getState().upsert(CASE_CARDS[0]);
    renderHook(() => useSeedCases());
    expect(Object.keys(useCaseStore.getState().cases)).toHaveLength(1);
  });

  it('threadStore가 비어있으면 THREADS로 시드한다', () => {
    renderHook(() => useSeedThreads());
    expect(Object.keys(useThreadStore.getState().threads)).toHaveLength(THREADS.length);
  });

  it('threadStore에 이미 데이터가 있으면 다시 시드하지 않는다', () => {
    useThreadStore.getState().upsert(THREADS[0]);
    renderHook(() => useSeedThreads());
    expect(Object.keys(useThreadStore.getState().threads)).toHaveLength(1);
  });
});

// SD-3 — mock 모드에서 useSeedCitations/useSeedBriefing은 아무 것도 하지 않아야 한다(fetch
// 호출 없음, 기존 렌더 동작 100% 보존). citationStore는 CITATION_LIBRARY로 이미 채워진 채
// 시작하므로 "값이 안 바뀐다"까지 확인한다.
describe('useSeedCitations / useSeedBriefing — mock 모드', () => {
  beforeEach(() => {
    useCitationStore.getState().reset();
    useBriefingStore.getState().reset();
  });

  it('mock 모드에서는 fetch를 호출하지 않고 citationStore가 mock 값 그대로다', () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;
    renderHook(() => useSeedCitations());
    expect(fetchMock).not.toHaveBeenCalled();
    expect(useCitationStore.getState().records).toEqual(CITATION_LIBRARY);
  });

  it('mock 모드에서는 fetch를 호출하지 않고 briefingStore가 비어 있다', () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;
    renderHook(() => useSeedBriefing());
    expect(fetchMock).not.toHaveBeenCalled();
    expect(useBriefingStore.getState().briefing).toBeNull();
  });
});

// R5.4 — mock 모드는 notificationStore를 절대 건드리지 않는다(BriefingHomePage
// unreadNotifications:0 무변경 보장의 근거).
describe('useSeedNotifications — mock 모드', () => {
  beforeEach(() => useNotificationStore.getState().reset());

  it('mock 모드에서는 아무 것도 hydrate하지 않는다', () => {
    renderHook(() => useSeedNotifications());
    expect(useNotificationStore.getState().records).toEqual([]);
  });
});
