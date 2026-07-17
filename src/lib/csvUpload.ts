import type { CaseCard } from '@/types';

// CSV 일괄 등록(4.4) — reference/design-system/외고반장 CSV 업로드.dc.html §1a 이식.
// 실제 파일 파싱 백엔드가 없어 "업로드"는 고정 샘플 8행을 검증→등록하는 각본이다
// (RunEngine 각본 철학과 동일). 외국인등록번호는 화면 어디에도 원문을 들일 경로를
// 만들지 않는다는 온보딩 O4의 결정을 그대로 따라 — 이 fixture부터 이미 마스킹된
// 문자열(`lib/mask.ts` 규칙과 동일 형식)로만 존재한다(GOTCHAS §1).
export type RowStatus = 'normal' | 'warn' | 'error';

export interface CsvRow {
  rowNo: number;
  name: string;
  nationality: string;
  team: string;
  stayExpiryDateRaw: string; // 파일에 적힌 그대로(형식이 틀릴 수 있음) — 빈 문자열=누락
  externalRegNoMasked: string; // 이미 마스킹된 값만 존재
}

export interface ValidatedCsvRow extends CsvRow {
  status: RowStatus;
  reason?: string;
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

// 샘플 업로드 파일(8행) — 6인 로스터(정상) + 형식 경고 1건 + 필수값 누락 1건.
// 6인 로스터는 mocks/fixtures.ts CASE_CARDS의 workerRef와 동일 인물이지만, 등록은
// 별도 caseId(imp- 접두)로 들어가 기존 시드 케이스를 덮어쓰지 않는다(멱등·비파괴).
export const SAMPLE_CSV_ROWS: CsvRow[] = [
  { rowNo: 1, name: 'Batbayar E.', nationality: '몽골', team: '제조2팀', stayExpiryDateRaw: '2026-07-08', externalRegNoMasked: '******-*******' },
  { rowNo: 2, name: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', stayExpiryDateRaw: '2026-08-09', externalRegNoMasked: '******-*******' },
  { rowNo: 3, name: 'Siti R.', nationality: '인도네시아', team: '포장팀', stayExpiryDateRaw: '2027-02-14', externalRegNoMasked: '******-*******' },
  { rowNo: 4, name: 'Tran Thi H.', nationality: '베트남', team: '품질팀', stayExpiryDateRaw: '2026-09-15', externalRegNoMasked: '******-*******' },
  { rowNo: 5, name: 'Rahmat P.', nationality: '인도네시아', team: '제조1팀', stayExpiryDateRaw: '2026-11-05', externalRegNoMasked: '******-*******' },
  { rowNo: 6, name: 'Oyunaa T.', nationality: '몽골', team: '포장팀', stayExpiryDateRaw: '2026-09-23', externalRegNoMasked: '******-*******' },
  { rowNo: 7, name: 'Pham Duc M.', nationality: '베트남', team: '제조2팀', stayExpiryDateRaw: '2026.8.9', externalRegNoMasked: '******-*******' },
  { rowNo: 8, name: 'Kyaw Zin', nationality: '미얀마', team: '포장팀', stayExpiryDateRaw: '', externalRegNoMasked: '******-*******' },
];

// 필수 컬럼 누락(헤더 누락과 동치 — 값이 비어 있으면 그 컬럼이 없는 것과 같다)·중복 이름
// (사번이 없는 데이터 모델이라 "이름"을 유일 식별자로 대체)·날짜 형식만 검증한다.
// 오류(error) > 경고(warn) 우선순위 — 둘 다 걸리면 오류로 표시.
export function validateRows(rows: CsvRow[]): ValidatedCsvRow[] {
  const nameCounts = new Map<string, number>();
  for (const row of rows) nameCounts.set(row.name, (nameCounts.get(row.name) ?? 0) + 1);

  return rows.map((row) => {
    const missingField = (['name', 'nationality', 'team', 'stayExpiryDateRaw', 'externalRegNoMasked'] as const).find(
      (key) => row[key].trim().length === 0,
    );
    if (missingField) {
      const LABEL: Record<typeof missingField, string> = {
        name: '이름',
        nationality: '국적',
        team: '팀',
        stayExpiryDateRaw: '체류만료일',
        externalRegNoMasked: '외국인등록번호',
      };
      return { ...row, status: 'error', reason: `${LABEL[missingField]} 값이 없습니다` };
    }
    if ((nameCounts.get(row.name) ?? 0) > 1) {
      return { ...row, status: 'error', reason: '이름이 중복되었습니다' };
    }
    if (!ISO_DATE.test(row.stayExpiryDateRaw)) {
      return { ...row, status: 'warn', reason: `체류만료일 형식 확인이 필요합니다 (${row.stayExpiryDateRaw} 입력됨)` };
    }
    return { ...row, status: 'normal' };
  });
}

// CSV 양식 안내(CsvUploadWorkbench aside)와 다운로드 템플릿이 공유하는 단일 소스 — 코드리뷰
// 지적: 이전엔 이 5개 컬럼을 화면(JSX 배열)과 여기(문자열) 두 곳에 각자 하드코딩해, 컬럼이
// 추가·변경될 때 한쪽만 고치면 조용히 어긋날 수 있었다.
export const CSV_TEMPLATE_COLUMNS = ['이름', '국적', '팀', '체류만료일 (YYYY-MM-DD)', '외국인등록번호'] as const;
export const CSV_TEMPLATE_HEADER = CSV_TEMPLATE_COLUMNS.join(',');
const CSV_TEMPLATE_FILENAME = '근로자_등록_템플릿.csv';

// NEXT_ROADMAP B-4: "템플릿 다운로드" 버튼에 onClick이 없어 죽은 버튼이었다 — 실제 파일
// 업로드 백엔드가 없는 것과 별개로, 헤더만 담은 정적 CSV는 클라이언트에서 바로 만들 수 있다.
// data: URI를 쓰는 이유는 jsdom에 미구현인 URL.createObjectURL 없이도 동작하기 때문이다.
export function downloadCsvTemplate(): void {
  const link = document.createElement('a');
  link.href = `data:text/csv;charset=utf-8,${encodeURIComponent(`${CSV_TEMPLATE_HEADER}\n`)}`;
  link.download = CSV_TEMPLATE_FILENAME;
  link.click();
}

function slugFor(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9가-힣]+/g, '-').replace(/^-+|-+$/g, '');
}

// 근로자 1명 입력 — CSV 일괄 등록과 온보딩 O4(R1.2)가 공유하는 데이터 계약
// (NEXT_ROADMAP 1.2 "CSV와 동일한 데이터 계약 공유").
export interface WorkerInput {
  name: string;
  nationality: string;
  team: string;
  stayExpiryDate: string;
}

// 근로자 1명 → CaseCard 변환 — 아직 특정 이슈가 없는 저단계 확인 케이스로 시작한다
// (oyunaa 템플릿과 동일 모양). idPrefix로 진입점별 caseId 네임스페이스만 분리한다
// (CSV는 'imp', 온보딩 O4는 'onboard' — 픽스처 caseId와 충돌하지 않는다).
export function workerToCard(worker: WorkerInput, idPrefix: string): CaseCard {
  const id = `${idPrefix}-${slugFor(worker.name)}`;
  return {
    caseId: id,
    caseCode: `case_${id}`,
    title: '근로자 등록 확인',
    workerRef: { displayName: worker.name, nationality: worker.nationality, team: worker.team, maskLevel: 'masked' },
    severity: 'LOW',
    stayExpiryDate: worker.stayExpiryDate,
    agentStage: 'detected',
    state: 'draft',
    approvalRequired: false,
    primaryAction: { actionId: `${id}-detail`, label: '상세 보기', state: 'ready', requiresApproval: false, kind: 'detail' },
    secondaryAction: { actionId: `${id}-confirm`, label: '케이스 확인 완료', state: 'ready', requiresApproval: false, kind: 'confirm' },
    preparedBy: 'rule',
  };
}

// 정상 판정 행만 CaseCard로 변환 — 경고·오류 행은 등록하지 않는다(브리프 가드레일).
export function rowsToCards(rows: ValidatedCsvRow[]): CaseCard[] {
  return rows
    .filter((row): row is ValidatedCsvRow & { status: 'normal' } => row.status === 'normal')
    .map((row) => ({
      ...workerToCard(
        { name: row.name, nationality: row.nationality, team: row.team, stayExpiryDate: row.stayExpiryDateRaw },
        'imp',
      ),
      caseCode: `case_imp_${row.rowNo}`, // 행 번호 기반 표기는 CSV 고유 관례라 그대로 유지.
    }));
}
