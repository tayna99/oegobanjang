import { act } from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { PackagePage } from './PackagePage';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

afterEach(() => {
  useApprovalStore.getState().reset();
  useEvidenceStore.getState().reset();
  useRoleStore.getState().reset();
});

function renderAt(path = '/package/batbayar') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/package/:packageId" element={<PackagePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// 2.4 행정사 패키지(관제형 §2d) — 포함 항목·검토 요청서·PII 마스킹·승인 게이트 내보내기.
describe('PackagePage', () => {
  it('검토 요청서와 포함 항목·근거·이력을 렌더한다', () => {
    renderAt();
    expect(screen.getByRole('heading', { name: '행정사 검토 패키지' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '행정사 검토 요청서' })).toBeInTheDocument();
    expect(screen.getByLabelText('포함 항목')).toBeInTheDocument();
    // 근거 각주 cit_ 참조.
    const doc = screen.getByRole('region', { name: '검토 요청서' });
    expect(within(doc).getByText(/cit_003/)).toBeInTheDocument();
    // 내보내기 이력 해시.
    expect(screen.getByText(/export_0031 · sha256:aa72…3c19/)).toBeInTheDocument();
  });

  it('외국인등록번호는 완전히 마스킹된 값만 표기한다(원문 숫자 없음)', () => {
    renderAt();
    const doc = screen.getByRole('region', { name: '검토 요청서' });
    const line = within(doc).getByText(/외국인등록번호:/);
    // 코드리뷰 지적: 부분 원문("900412-6")이 하드코딩되어 있었다 — 숫자가 전혀 없어야 한다.
    expect(line.textContent).not.toMatch(/\d/);
  });

  it('내보내기는 승인 전 잠금 — 승인 없으면 disabled', () => {
    renderAt();
    expect(screen.getByRole('button', { name: '내보내기 (승인 필요)' })).toBeDisabled();
  });

  it('승인 요청 시 evidence(approval_requested)가 기록되고 버튼이 잠긴다', () => {
    renderAt();
    fireEvent.click(screen.getByRole('button', { name: '승인 요청' }));
    expect(screen.getByRole('button', { name: '승인 요청됨' })).toBeDisabled();
    const types = useEvidenceStore.getState().events.map((e) => e.type);
    expect(types).toContain('approval_requested');
  });

  it('승인된 패키지는 내보내기가 활성화된다', () => {
    useApprovalStore.getState().requestApproval('batbayar-handoff-export');
    useApprovalStore.getState().decide('batbayar-handoff-export', 'approved', 'k1');
    renderAt();
    expect(screen.getByRole('button', { name: '내보내기' })).toBeEnabled();
  });

  it('내보내기 클릭 시 evidence(exported)가 기록된다', () => {
    useApprovalStore.getState().requestApproval('batbayar-handoff-export');
    useApprovalStore.getState().decide('batbayar-handoff-export', 'approved', 'k1');
    renderAt();
    fireEvent.click(screen.getByRole('button', { name: '내보내기' }));
    const types = useEvidenceStore.getState().events.map((e) => e.type);
    expect(types).toContain('exported');
  });

  it('포함 항목을 해제하면 문서에서 해당 섹션이 빠진다', () => {
    renderAt();
    const doc = screen.getByRole('region', { name: '검토 요청서' });
    expect(within(doc).getByText('2. 누락 서류')).toBeInTheDocument();
    // "누락 서류 목록" 항목 체크 해제.
    fireEvent.click(screen.getByRole('checkbox', { name: /누락 서류 목록/ }));
    expect(within(doc).queryByText('2. 누락 서류')).not.toBeInTheDocument();
  });
});

// 7단계 §4 — 행정사 패키지 링크 만료·재발급·열람 로그(운영급 RBAC 확장).
describe('PackagePage — 링크 만료·재발급·열람 로그', () => {
  it('발급 후 7일 이내면 만료 안내가 없다(batbayar는 2026-07-06 발급)', () => {
    renderAt();
    expect(screen.queryByText(/행정사 링크가 만료되었습니다/)).not.toBeInTheDocument();
  });

  it('manager는 링크 재발급 버튼을 보고, 클릭하면 package_link_issued evidence가 남는다', () => {
    renderAt();
    const reissueButton = screen.getByRole('button', { name: '링크 재발급' });
    fireEvent.click(reissueButton);
    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'package_link_issued' && e.caseId === 'batbayar'),
    ).toBe(true);
  });

  it('owner는 링크 재발급 버튼을 보지 않는다(7단계 §4 "재발급은 manager")', () => {
    useRoleStore.getState().setRole('owner');
    renderAt();
    expect(screen.queryByRole('button', { name: '링크 재발급' })).not.toBeInTheDocument();
  });

  it('열람 로그가 없으면 안내 문구, package_link_viewed가 쌓이면 목록에 표시된다', () => {
    renderAt();
    expect(screen.getByText('아직 행정사가 링크를 열람하지 않았습니다.')).toBeInTheDocument();

    // 같은 렌더 인스턴스가 스토어 갱신에 반응하는지 확인 — 재렌더하지 않는다.
    act(() => {
      useEvidenceStore.getState().append({
        id: 'view-1',
        type: 'package_link_viewed',
        at: new Date().toISOString(),
        caseId: 'batbayar',
        summary: '행정사가 패키지 링크 열람 · 김앤리 행정사무소',
      });
    });
    expect(screen.getByText('행정사가 패키지 링크 열람 · 김앤리 행정사무소')).toBeInTheDocument();
  });
});
