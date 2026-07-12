import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { PackagePage } from './PackagePage';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

afterEach(() => {
  useApprovalStore.getState().reset();
  useEvidenceStore.getState().reset();
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

  it('외국인등록번호는 마스킹 값만 표기한다(원문 없음)', () => {
    renderAt();
    expect(screen.getByText(/외국인등록번호: 900412-6●●●●●●/)).toBeInTheDocument();
    // 마스킹 안 된 6자리 뒷자리가 없어야 한다.
    expect(screen.queryByText(/900412-6\d{6}/)).not.toBeInTheDocument();
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

  it('포함 항목을 해제하면 문서에서 해당 섹션이 빠진다', () => {
    renderAt();
    const doc = screen.getByRole('region', { name: '검토 요청서' });
    expect(within(doc).getByText('2. 누락 서류')).toBeInTheDocument();
    // "누락 서류 목록" 항목 체크 해제.
    fireEvent.click(screen.getByRole('checkbox', { name: /누락 서류 목록/ }));
    expect(within(doc).queryByText('2. 누락 서류')).not.toBeInTheDocument();
  });
});
