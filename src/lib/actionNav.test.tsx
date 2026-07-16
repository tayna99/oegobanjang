import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { MemoryRouter, useLocation, type Location } from 'react-router-dom';
import { useEffect } from 'react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useNextAction } from './actionNav';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { NextActionRef } from '@/types';

function LocationRecorder({ onChange }: { onChange: (location: Location) => void }) {
  const location = useLocation();
  useEffect(() => {
    onChange(location);
  }, [location, onChange]);
  return null;
}

function setup() {
  let current: Location | undefined;
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={['/']}>
      <LocationRecorder onChange={(l) => (current = l)} />
      {children}
    </MemoryRouter>
  );
  return { wrapper, getLocation: () => current };
}

function action(kind: NextActionRef['kind']): NextActionRef {
  return { actionId: 'a1', label: 'l', state: 'ready', requiresApproval: false, kind };
}

describe('useNextAction', () => {
  beforeEach(() => {
    useEvidenceStore.getState().reset();
  });

  it('approve는 승인 직전 화면으로 이동한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNextAction(), { wrapper });
    act(() => result.current('nguyen', action('approve')));
    expect(getLocation()?.pathname).toBe('/case/nguyen/approve');
  });

  it('draft는 초안 화면으로 이동한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNextAction(), { wrapper });
    act(() => result.current('nguyen', action('draft')));
    expect(getLocation()?.pathname).toBe('/case/nguyen/draft');
  });

  it('detail은 케이스 시트로 이동한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNextAction(), { wrapper });
    act(() => result.current('batbayar', action('detail')));
    expect(getLocation()?.pathname).toBe('/case/batbayar');
  });

  it('thread는 threadIdForCase 매핑이 있으면 해당 스레드(M6)로 이동한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNextAction(), { wrapper });
    act(() => result.current('tranCase', action('thread')));
    expect(getLocation()?.pathname).toBe('/thread/tran');
  });

  it('thread는 threadIdForCase 매핑이 없으면 메시지 탭으로 폴백한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNextAction(), { wrapper });
    act(() => result.current('bayar-no-thread-mapping', action('thread')));
    expect(getLocation()?.pathname).toBe('/messages');
  });

  it('package는 행정사 패키지 화면으로 이동한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNextAction(), { wrapper });
    act(() => result.current('batbayar', action('package')));
    expect(getLocation()?.pathname).toBe('/package/batbayar');
  });

  it('confirm은 이동하지 않고 evidence 이벤트만 남긴다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNextAction(), { wrapper });
    act(() => result.current('tranCase', action('confirm')));
    expect(getLocation()?.pathname).toBe('/');
    const events = useEvidenceStore.getState().events;
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ type: 'approval_decided', caseId: 'tranCase', actionId: 'a1' });
  });
});
