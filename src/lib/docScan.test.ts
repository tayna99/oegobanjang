import { describe, expect, it } from 'vitest';
import { classifyScanFiles, hasUnresolvedRows } from './docScan';
import type { CaseCard } from '@/types';

function worker(displayName: string, caseId: string): CaseCard {
  return {
    caseId,
    caseCode: `case_${caseId}`,
    title: 't',
    workerRef: { displayName, nationality: '베트남', maskLevel: 'masked' },
    severity: 'LOW',
    state: 'draft',
    approvalRequired: false,
    primaryAction: { actionId: 'a1', label: 'l', state: 'ready', requiresApproval: false, kind: 'detail' },
    secondaryAction: { actionId: 'a2', label: 'l', state: 'ready', requiresApproval: false, kind: 'detail' },
    preparedBy: 'rule',
  };
}

describe('classifyScanFiles', () => {
  const workers = [worker('Nguyen Van A', 'nguyen'), worker('Tran Thi H.', 'tranCase')];

  it('파일명에 근로자와 서류 키워드가 모두 있으면 정상 매칭이다', () => {
    const [result] = classifyScanFiles(['nguyen_passport.jpg'], workers);
    expect(result.status).toBe('matched');
    expect(result.workerName).toBe('Nguyen Van A');
    expect(result.docType).toBe('여권 사본');
  });

  it('서류 키워드만 있으면 확인 필요(신뢰도 낮음)다', () => {
    const [result] = classifyScanFiles(['scan_contract.jpg'], workers);
    expect(result.status).toBe('low_confidence');
    expect(result.docType).toBe('고용계약서');
    expect(result.workerName).toBeUndefined();
  });

  it('근로자 키워드만 있어도 확인 필요다', () => {
    const [result] = classifyScanFiles(['tran_0002.jpg'], workers);
    expect(result.status).toBe('low_confidence');
    expect(result.workerName).toBe('Tran Thi H.');
    expect(result.docType).toBeUndefined();
  });

  it('아무 키워드도 없으면 미매칭(근로자 매칭 실패)이다', () => {
    const [result] = classifyScanFiles(['scan_0006.jpg'], workers);
    expect(result.status).toBe('unmatched');
    expect(result.workerName).toBeUndefined();
    expect(result.docType).toBeUndefined();
  });

  it('분류 결과는 입력 순서 그대로 결정적이다', () => {
    const files = ['scan_0006.jpg', 'nguyen_passport.jpg', 'scan_contract.jpg'];
    const results = classifyScanFiles(files, workers);
    expect(results.map((r) => r.fileName)).toEqual(files);
    expect(results.map((r) => r.status)).toEqual(['unmatched', 'matched', 'low_confidence']);
  });
});

describe('hasUnresolvedRows', () => {
  it('미매칭(근로자 미지정) 행이 있으면 true다', () => {
    expect(hasUnresolvedRows([{ fileId: '1', fileName: 'x', status: 'unmatched' }])).toBe(true);
  });

  it('근로자와 서류 유형이 모두 지정된 저신뢰 행만 false다', () => {
    expect(hasUnresolvedRows([{ fileId: '1', fileName: 'x', status: 'low_confidence', workerName: 'Oyunaa T.', docType: '여권 사본' }])).toBe(false);
  });

  it('근로자만 지정되고 서류 유형이 없으면 true다', () => {
    expect(hasUnresolvedRows([{ fileId: '1', fileName: 'x', status: 'low_confidence', workerName: 'Oyunaa T.' }])).toBe(true);
  });

  it('전부 정상 매칭이면 false다', () => {
    expect(hasUnresolvedRows([{ fileId: '1', fileName: 'x', status: 'matched', workerName: 'a', docType: 'b' }])).toBe(false);
  });
});
