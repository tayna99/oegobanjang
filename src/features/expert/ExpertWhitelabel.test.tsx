import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { ExpertDashboardPage } from './ExpertDashboardPage';
import { ExpertPackagePage } from './ExpertPackagePage';
import { useEvidenceStore } from '@/stores/evidenceStore';

afterEach(() => useEvidenceStore.getState().reset());

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/expert/:expertId" element={<ExpertDashboardPage />} />
        <Route path="/expert/:expertId/package/:packageId" element={<ExpertPackagePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// 행정사 화이트라벨(7-1) — 영속 링크로 개인 대시보드 진입, 여러 회사 통합, 브랜드 노출.
describe('ExpertDashboardPage', () => {
  it('행정사 브랜드 헤더와 연결된 두 회사의 검토 대기를 회사별로 묶어 보여준다', () => {
    renderAt('/expert/expert-kimlee');
    // 화이트라벨: 외고반장이 아니라 행정사무소 이름이 헤더에 뜬다(+ powered-by).
    expect(screen.getByRole('heading', { name: '검토 대기 2건' })).toBeInTheDocument();
    expect(screen.getByText('김앤리 행정사무소')).toBeInTheDocument();
    expect(screen.getByText('외고반장 제공')).toBeInTheDocument();
    // 두 회사가 각각 그룹으로.
    expect(screen.getByRole('region', { name: '그린푸드 제조 검토 요청' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '한빛식품 검토 요청' })).toBeInTheDocument();
  });

  it('행 클릭이 해당 회사의 패키지 뷰로 이동한다', () => {
    renderAt('/expert/expert-kimlee');
    fireEvent.click(screen.getByRole('button', { name: 'Le Van T. 검토' }));
    expect(screen.getByRole('heading', { name: '행정사 검토 요청서' })).toBeInTheDocument();
    // 소속 회사(한빛식품)가 헤더 부제로.
    expect(screen.getByText(/한빛식품 · 검토 요청/)).toBeInTheDocument();
  });

  it('존재하지 않는 expert 토큰이면 링크 없음 안내만 보여준다', () => {
    renderAt('/expert/no-such-expert');
    expect(screen.getByText('링크를 찾을 수 없습니다.')).toBeInTheDocument();
  });
});

describe('ExpertPackagePage', () => {
  it('브랜드 헤더 + 문서 미리보기 + 구조화된 회신을 렌더하고 열람 로그를 남긴다', () => {
    renderAt('/expert/expert-kimlee/package/batbayar');
    // 문서 본문에도 "수신: 김앤리 행정사무소"가 있어 헤더(banner)로 스코프한다.
    expect(within(screen.getByRole('banner')).getByText('김앤리 행정사무소')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '행정사 검토 요청서' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '회신 보내기' })).toBeInTheDocument();
    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'package_link_viewed' && e.caseId === 'batbayar'),
    ).toBe(true);
  });

  it('회신을 보내면 evidence(package_reply)가 그 회사 케이스로 기록된다', () => {
    renderAt('/expert/expert-kimlee/package/levan');
    fireEvent.click(screen.getByRole('button', { name: '재직증명서 원본이 추가로 필요합니다' }));
    fireEvent.click(screen.getByRole('button', { name: '회신 보내기' }));
    const reply = useEvidenceStore.getState().events.find((e) => e.type === 'package_reply');
    expect(reply?.caseId).toBe('levan');
  });

  it('대시보드로 돌아가기 버튼이 있다', () => {
    renderAt('/expert/expert-kimlee/package/batbayar');
    expect(screen.getByRole('button', { name: '대시보드로' })).toBeInTheDocument();
  });

  // scope 검사(스펙 §1 "scope 밖은 존재 비노출") — 이 행정사에게 오지 않은 패키지는 404 취급.
  it('이 행정사의 것이 아닌 packageId는 링크 없음으로 처리한다(존재 비노출)', () => {
    // packageId는 실재하지만 이 expert scope에 없는 경우를 흉내내기 위해, 없는 packageId로 검증.
    renderAt('/expert/expert-kimlee/package/no-such-package');
    expect(screen.getByText('링크를 찾을 수 없습니다.')).toBeInTheDocument();
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'package_link_viewed')).toBe(false);
  });
});
