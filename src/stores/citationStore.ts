import { create } from 'zustand';
import type { Citation, CitationRecord } from '@/types';
import { CITATION_LIBRARY } from '@/mocks/citations';

// 근거 라이브러리 스토어 — PC §3c 거버넌스(2.5.5)의 데이터 소스 (2.5.4b, 블루프린트 §3).
// KPI·연계 케이스 수는 저장하지 않고 셀렉터로 파생한다(ROADMAP 2.5.5 DoD "KPI=스토어 파생값").

// F등급(합성 데이터)은 근거로 사용 불가 — 디자인 §3c 각주, 2026-07-11 비준.
// citation-0 승인 잠금 판정 등 "근거로 세는" 모든 곳은 이 필터를 거친다.
export function usableCitations<T extends Citation>(citations: T[]): T[] {
  return citations.filter((citation) => citation.grade !== 'F');
}

export interface CitationLibraryKpis {
  total: number;
  official: number; // 공식 근거 (A·B)
  fresh: number; // 최신성 확인 (stale 아님)
  reviewNeeded: number; // 검토 필요
  stale: number; // 부족 (stale)
}

interface CitationStoreState {
  records: CitationRecord[];
  register: (record: CitationRecord) => void;
  /** SD-3 — real 모드 부팅/화면 진입 시 서버 근거 라이브러리로 전량 교체(seed 전용, 재기록
   * 아님). mock 레코드와 병합하지 않는다 — fetchCases가 mock CASE_CARDS를 완전히 대체하는
   * 것과 동일 원칙(mergeSeedAndRuntime real 가드와 대칭). */
  hydrate: (records: CitationRecord[]) => void;
  reset: () => void;
}

export const useCitationStore = create<CitationStoreState>((set) => ({
  records: CITATION_LIBRARY,
  register: (record) =>
    set((s) => ({
      records: s.records.some((r) => r.id === record.id)
        ? s.records.map((r) => (r.id === record.id ? record : r))
        : [...s.records, record],
    })),
  hydrate: (records) => set({ records }),
  reset: () => set({ records: CITATION_LIBRARY }),
}));

export function citationKpis(records: CitationRecord[]): CitationLibraryKpis {
  return {
    total: records.length,
    official: records.filter((r) => r.grade === 'A' || r.grade === 'B').length,
    fresh: records.filter((r) => r.status !== 'stale').length,
    reviewNeeded: records.filter((r) => r.status === 'review_needed').length,
    stale: records.filter((r) => r.status === 'stale').length,
  };
}

// 연계 케이스 수 — 케이스 시트들의 참조에서 파생(§3c '연계 케이스' 컬럼).
export function linkedCaseCount(
  recordId: string,
  sheets: Array<{ citations: Citation[] }>,
): number {
  // F등급 참조는 "연계"로 세지 않는다 — citation-lock 판정과 동일 규칙(코드리뷰 지적).
  return sheets.filter((sheet) => usableCitations(sheet.citations).some((c) => c.id === recordId)).length;
}
