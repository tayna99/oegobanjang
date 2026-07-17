import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useSeedCases, useSeedThreads } from './dataSeed';
import { CASE_CARDS } from '@/mocks/fixtures';
import { THREADS } from '@/mocks/threads';
import { useCaseStore } from '@/stores/caseStore';
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
