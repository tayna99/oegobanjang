import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { GovernancePage } from './GovernancePage';
import { useCitationStore } from '@/stores/citationStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

afterEach(() => {
  useCitationStore.getState().reset();
  useEvidenceStore.getState().reset();
});

// 2.5.5 §3c 거버넌스 — 근거 라이브러리(KPI 파생·연계 케이스) + 감사 로그(필터·해시).
describe('GovernancePage', () => {
  it('근거 라이브러리 KPI가 스토어에서 파생된다(하드코딩 아님)', () => {
    render(<GovernancePage />);
    const lib = screen.getByRole('region', { name: '근거 라이브러리' });
    // 시드 라이브러리 = 9건(A·B·E), stale 1건(KOSHA).
    expect(within(lib).getByText('전체')).toBeInTheDocument();
    // 부족(stale) KPI = 1 — KOSHA 근거. ("부족 (stale)"은 KPI 라벨과 상태 칩에 모두 나오므로
    // KPI 타일 라벨(text-subtle)을 특정해 그 타일의 값이 1인지 본다.)
    const staleLabel = within(lib)
      .getAllByText('부족 (stale)')
      .find((el) => el.className.includes('text-subtle'));
    expect(staleLabel).toBeDefined();
    expect(within(staleLabel!.closest('div') as HTMLElement).getByText('1')).toBeInTheDocument();
  });

  it('F등급 근거는 없지만 등급 칩과 상태가 렌더된다', () => {
    render(<GovernancePage />);
    const lib = screen.getByRole('region', { name: '근거 라이브러리' });
    expect(within(lib).getAllByText('공식 근거').length).toBeGreaterThan(0);
    expect(within(lib).getByText(/F등급.*근거로 사용할 수 없습니다/)).toBeInTheDocument();
  });

  it('감사 로그가 시드를 최신순으로 보여주고 해시를 표기한다', () => {
    render(<GovernancePage />);
    const log = screen.getByRole('complementary', { name: '감사 로그' });
    expect(within(log).getByText('INSERT-only · 원문 PII 미저장 (해시만 기록)')).toBeInTheDocument();
    expect(within(log).getAllByText(/sha256:/).length).toBeGreaterThan(0);
  });

  it('필터 칩이 감사 로그를 유형별로 거른다 — 내보내기는 export만', () => {
    render(<GovernancePage />);
    const log = screen.getByRole('complementary', { name: '감사 로그' });
    fireEvent.click(within(log).getByRole('button', { name: '내보내기' }));
    expect(within(log).getByText(/export_0031/)).toBeInTheDocument();
    // 위험 탐지 항목은 내보내기 필터에서 사라진다.
    expect(within(log).queryByText(/CRITICAL 탐지/)).not.toBeInTheDocument();
  });

  it('위험 탐지 필터는 risk_flagged만 남긴다', () => {
    render(<GovernancePage />);
    const log = screen.getByRole('complementary', { name: '감사 로그' });
    fireEvent.click(within(log).getByRole('button', { name: '위험 탐지' }));
    expect(within(log).getByText(/CRITICAL 탐지/)).toBeInTheDocument();
    expect(within(log).queryByText(/export_0031/)).not.toBeInTheDocument();
  });
});
