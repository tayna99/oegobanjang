import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { CaseSheet } from './CaseSheet';
import type { CaseCard } from '@/types';
import type { CaseSheet as CaseSheetData } from '@/mocks/fixtures';

const CARD: CaseCard = {
  caseId: 'nguyen',
  title: 'Nguyen V. 체류기간 연장 서류 요청',
  severity: 'HIGH',
  dDay: 30,
  missingDocCount: 2,
  state: 'approval_pending',
  approvalRequired: true,
  primaryAction: { actionId: 'a', label: '승인하기', state: 'ready', requiresApproval: true, kind: 'approve' },
  secondaryAction: { actionId: 'b', label: '초안 보기', state: 'ready', requiresApproval: false, kind: 'draft' },
  preparedBy: 'agent',
  preparedRunRef: '#4788',
};

const SHEET: CaseSheetData = {
  caseId: 'nguyen',
  summary: '체류만료가 30일 남았고 서류 2건이 누락되어 요청이 필요합니다.',
  checkedItems: [{ label: '체류만료일', value: '2026.08.03 · D-30' }],
  docs: [{ name: '여권 사본', status: 'missing', statusLabel: '누락' }],
  citations: [{ grade: 'A', title: '출입국관리법 제25조', source: '국가법령정보센터', updatedAt: '2025.11' }],
  activity: [{ label: '서류요청 준비', detail: 'D-30 감지', at: '오늘 07:58', outcome: 'pending', runRef: '#4788' }],
  nextWake: '다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다',
};

function renderSheet(sheet: CaseSheetData, card: CaseCard = CARD) {
  return render(
    <MemoryRouter>
      <CaseSheet card={card} sheet={sheet} open onClose={vi.fn()} />
    </MemoryRouter>,
  );
}

describe('CaseSheet', () => {
  it('5블록(요약·AI확인내용·서류체크리스트·근거·에이전트활동)을 전부 렌더한다', () => {
    renderSheet(SHEET);
    expect(screen.getByText(CARD.title)).toBeInTheDocument();
    expect(screen.getByText(SHEET.summary)).toBeInTheDocument();
    expect(screen.getByText('체류만료일')).toBeInTheDocument();
    expect(screen.getByText('여권 사본')).toBeInTheDocument();
    expect(screen.getByText('출입국관리법 제25조')).toBeInTheDocument();
    expect(screen.getByText('서류요청 준비')).toBeInTheDocument();
    expect(screen.getByText(/발송 후 2일간/)).toBeInTheDocument();
  });

  it('ActionBar는 CTA 2개(secondary + primary)를 렌더한다', () => {
    renderSheet(SHEET);
    expect(screen.getByRole('button', { name: '초안 보기' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '승인하기' })).toBeInTheDocument();
  });

  it('citation이 0건이면 근거 경고를 보여주고 승인 버튼을 잠근다(DoD)', () => {
    renderSheet({ ...SHEET, citations: [] });
    expect(screen.getByText(/공식 근거가 연결되지 않았습니다/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '승인하기' })).toBeDisabled();
  });

  it('citation이 1건 이상이면 승인 버튼이 잠기지 않는다', () => {
    renderSheet(SHEET);
    expect(screen.getByRole('button', { name: '승인하기' })).not.toBeDisabled();
  });

  it('guardNote가 있으면(고위험 케이스) 경고문을 보여준다', () => {
    renderSheet({ ...SHEET, guardNote: '기한 경과 케이스는 앱에서 처리할 수 없습니다' });
    expect(screen.getByText('기한 경과 케이스는 앱에서 처리할 수 없습니다')).toBeInTheDocument();
  });

  it('readinessPercent가 있으면 준비도를 보여준다', () => {
    renderSheet({ ...SHEET, readinessPercent: 62 });
    expect(screen.getByText('준비도 62%')).toBeInTheDocument();
  });
});
