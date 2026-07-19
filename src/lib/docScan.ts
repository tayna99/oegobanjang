// 서류 스캔 자동분류 — reference/design-system/design-briefs/서류스캔_업로드_브리프.md +
// docs/DESIGN_SYNC_AUDIT_2026-07-17.md §2. OCR 파이프라인이 없어 파일명 키워드로만
// 결정론적 분류한다(GOTCHAS §4 "시간·정렬은 deterministic" — 입력 순서 그대로, 랜덤 없음).
import type { CaseCard } from '@/types';

export type ScanMatchStatus = 'matched' | 'low_confidence' | 'unmatched';

export interface ScanResult {
  fileId: string;
  fileName: string;
  caseId?: string;
  workerName?: string;
  docType?: string;
  status: ScanMatchStatus;
}

// CASE_SHEETS(mocks/fixtures.ts)의 실제 서류명 어휘와 맞춘다(doc.name 키 계약,
// applyDocUpdatesOverlay가 이 이름으로 매칭한다).
export const SCAN_DOC_TYPES = ['여권 사본', '고용계약서', '재직증명서', '외국인등록증'] as const;

const DOC_KEYWORDS: Array<[string, (typeof SCAN_DOC_TYPES)[number]]> = [
  ['여권', '여권 사본'],
  ['passport', '여권 사본'],
  ['계약', '고용계약서'],
  ['contract', '고용계약서'],
  ['재직', '재직증명서'],
  ['등록증', '외국인등록증'],
];

function matchDocType(fileName: string): string | undefined {
  const lower = fileName.toLowerCase();
  return DOC_KEYWORDS.find(([keyword]) => lower.includes(keyword.toLowerCase()))?.[1];
}

// 근로자 이름의 첫 토큰(예: "Nguyen Van A" → "nguyen")이 파일명에 포함되는지로 매칭한다
// (CaseWorkbench.tsx의 이니셜 파생과 같은 결의 단순 토큰 매칭 — 실 OCR 대신 mock 근사).
function matchWorker(fileName: string, workers: CaseCard[]): CaseCard | undefined {
  const lower = fileName.toLowerCase();
  return workers.find((worker) => {
    const firstToken = worker.workerRef?.displayName.split(/[\s.]+/)[0];
    return !!firstToken && lower.includes(firstToken.toLowerCase());
  });
}

export function classifyScanFiles(fileNames: string[], workers: CaseCard[]): ScanResult[] {
  return fileNames.map((fileName, index) => {
    const docType = matchDocType(fileName);
    const worker = matchWorker(fileName, workers);
    const status: ScanMatchStatus = docType && worker ? 'matched' : docType || worker ? 'low_confidence' : 'unmatched';
    return {
      fileId: `scan-${index}`,
      fileName,
      caseId: worker?.caseId,
      workerName: worker?.workerRef?.displayName,
      docType,
      status,
    };
  });
}

// 확인 대기 반영 게이트 — CSV의 "정상만 자동 등록"과 다른 원칙이다(감사 §2.3). 미매칭 행이
// 남아있으면(근로자 미지정) 전체 확정 자체를 막는다 — 저신뢰(확인 필요) 행은 수정 없이도
// 함께 반영된다. 서류 확보 여부는 개별 근로자에게 중요해 자동 누락보다 사람의 전량 확인을
// 우선한다.
export function hasUnresolvedRows(results: ScanResult[]): boolean {
  return results.some((r) => r.status === 'unmatched' && !r.workerName);
}
