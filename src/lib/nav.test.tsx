import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { MemoryRouter, useLocation, type Location } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { useNav } from './nav';
import { useEffect } from 'react';

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

describe('useNav', () => {
  it('toCase가 케이스 상세 경로로 이동한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNav(), { wrapper });
    act(() => result.current.toCase('nguyen'));
    expect(getLocation()?.pathname).toBe('/case/nguyen');
  });

  it('toApprove가 승인 직전 경로로 이동한다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNav(), { wrapper });
    act(() => result.current.toApprove('nguyen'));
    expect(getLocation()?.pathname).toBe('/case/nguyen/approve');
  });

  it('toCases에 filter를 주면 쿼리 스트링이 붙는다', () => {
    const { wrapper, getLocation } = setup();
    const { result } = renderHook(() => useNav(), { wrapper });
    act(() => result.current.toCases('crit'));
    const l = getLocation();
    expect(`${l?.pathname}${l?.search}`).toBe('/cases?filter=crit');
  });
});
