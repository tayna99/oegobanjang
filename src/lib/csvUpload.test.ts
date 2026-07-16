import { describe, expect, it, vi } from 'vitest';
import { CSV_TEMPLATE_HEADER, downloadCsvTemplate, rowsToCards, SAMPLE_CSV_ROWS, validateRows } from './csvUpload';
import type { CsvRow } from './csvUpload';

// 4.4 DoD ① — "잘못된 행(헤더 누락·중복 사번) 검증 실패 테스트".
describe('validateRows', () => {
  it('필수 컬럼이 비어 있으면(헤더 누락과 동치) error로 판정한다', () => {
    const rows: CsvRow[] = [
      { rowNo: 1, name: 'Kyaw Zin', nationality: '미얀마', team: '포장팀', stayExpiryDateRaw: '', externalRegNoMasked: '******-*******' },
    ];
    const result = validateRows(rows);
    expect(result[0].status).toBe('error');
    expect(result[0].reason).toContain('체류만료일');
  });

  it('이름이 중복되면(사번 중복 대체) 두 행 모두 error로 판정한다', () => {
    const rows: CsvRow[] = [
      { rowNo: 1, name: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', stayExpiryDateRaw: '2026-08-09', externalRegNoMasked: '******-*******' },
      { rowNo: 2, name: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', stayExpiryDateRaw: '2026-08-10', externalRegNoMasked: '******-*******' },
    ];
    const result = validateRows(rows);
    expect(result[0].status).toBe('error');
    expect(result[1].status).toBe('error');
    expect(result[0].reason).toBe('이름이 중복되었습니다');
  });

  it('날짜 형식이 ISO(YYYY-MM-DD)가 아니면 warn — error가 아니다', () => {
    const rows: CsvRow[] = [
      { rowNo: 1, name: 'Pham Duc M.', nationality: '베트남', team: '제조2팀', stayExpiryDateRaw: '2026.8.9', externalRegNoMasked: '******-*******' },
    ];
    const result = validateRows(rows);
    expect(result[0].status).toBe('warn');
  });

  it('필수 값이 모두 있고 형식이 맞으면 normal이다', () => {
    const rows: CsvRow[] = [
      { rowNo: 1, name: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', stayExpiryDateRaw: '2026-08-09', externalRegNoMasked: '******-*******' },
    ];
    expect(validateRows(rows)[0].status).toBe('normal');
  });

  it('샘플 8행은 정상 6 · 경고 1 · 오류 1로 판정된다(목업 1a 결과와 동일 분포)', () => {
    const result = validateRows(SAMPLE_CSV_ROWS);
    expect(result.filter((r) => r.status === 'normal')).toHaveLength(6);
    expect(result.filter((r) => r.status === 'warn')).toHaveLength(1);
    expect(result.filter((r) => r.status === 'error')).toHaveLength(1);
  });
});

// 4.4 DoD ② — "성공 시 근로자 N명 스토어 반영 테스트"(반영 자체는 CsvUploadWorkbench.test에서 검증).
describe('rowsToCards', () => {
  it('정상 판정 행만 CaseCard로 변환하고, 경고·오류 행은 제외한다', () => {
    const cards = rowsToCards(validateRows(SAMPLE_CSV_ROWS));
    expect(cards).toHaveLength(6);
    expect(cards.every((c) => c.state === 'draft' && c.approvalRequired === false)).toBe(true);
    expect(cards.some((c) => c.workerRef?.displayName === 'Kyaw Zin')).toBe(false);
    expect(cards.some((c) => c.workerRef?.displayName === 'Pham Duc M.')).toBe(false);
  });

  it('caseId는 기존 시드 로스터의 짧은 id와 충돌하지 않는다(imp- 접두, 비파괴)', () => {
    const cards = rowsToCards(validateRows(SAMPLE_CSV_ROWS));
    expect(cards.some((c) => c.caseId === 'nguyen')).toBe(false);
    expect(cards.some((c) => c.caseId === 'imp-nguyen-van-a')).toBe(true);
  });
});

// NEXT_ROADMAP B-4 — "템플릿 다운로드" 죽은 버튼 수정(CsvUploadWorkbench.test.tsx의 클릭
// 상호작용 테스트와 별개로, 여기선 다운로드 링크 자체의 내용을 검증한다).
describe('downloadCsvTemplate', () => {
  it('CSV 양식 컬럼을 담은 data URI로 앵커를 만들어 클릭한다', () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    downloadCsvTemplate();

    expect(clickSpy).toHaveBeenCalledOnce();
    const anchor = clickSpy.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.download).toBe('근로자_등록_템플릿.csv');
    expect(decodeURIComponent(anchor.href)).toBe(`data:text/csv;charset=utf-8,${CSV_TEMPLATE_HEADER}\n`);

    clickSpy.mockRestore();
  });
});
