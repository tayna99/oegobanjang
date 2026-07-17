import { act } from 'react';
import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useOnboardingActions } from './onboarding';
import { CASE_CARDS } from '@/mocks/fixtures';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { CompanyProfile } from '@/types';

const PROFILE: CompanyProfile = { name: '그린푸드 제조', region: '경기 화성', industry: '식품 제조업', workerCount: '6명' };
const WORKER = { name: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', stayExpiryDate: '2026-08-09' };

describe('useOnboardingActions.completeOnboarding', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useCompanyStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  it('로스터 전체 + O4 입력 근로자를 caseStore에 반영하고(R1.2), 회사 프로필을 갱신하며(R1.1), evidence 1건을 남긴다', () => {
    const { result } = renderHook(() => useOnboardingActions());

    expect(useCaseStore.getState().cases.nguyen).toBeUndefined();

    act(() => result.current.completeOnboarding('manager', PROFILE, WORKER));

    const cases = useCaseStore.getState().cases;
    // 데모 세계관 6인 로스터 + O4에서 실제로 생성된 근로자 카드(onboard- 접두) 1건.
    expect(Object.keys(cases)).toHaveLength(CASE_CARDS.length + 1);
    expect(cases.nguyen).toBeDefined();
    expect(cases.nguyen.title).toBe('체류기간 연장 서류 요청');
    expect(cases['onboard-nguyen-van-a']?.workerRef?.displayName).toBe('Nguyen Van A');

    expect(useCompanyStore.getState().profile).toEqual(PROFILE);

    const events = useEvidenceStore.getState().events;
    expect(events.some((e) => e.type === 'plan_created' && e.actor === '담당자 김담당')).toBe(true);
  });

  it('멱등 — 두 번 호출해도 케이스 수가 늘지 않는다', () => {
    const { result } = renderHook(() => useOnboardingActions());
    act(() => result.current.completeOnboarding('owner', PROFILE, WORKER));
    act(() => result.current.completeOnboarding('owner', PROFILE, WORKER));
    expect(Object.keys(useCaseStore.getState().cases)).toHaveLength(CASE_CARDS.length + 1);
  });
});
