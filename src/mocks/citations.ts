// 근거 라이브러리 시드 — reference/design-system/외고반장 PC.dc.html §3c(503~575행) +
// §2d 각주(cit_003/007/021)·§3b 레일(cit_001/009/014) 이식 (2.5.4b, 블루프린트 §3).
// id는 디자인에 보이는 cit_* 번호를 그대로 쓴다. 케이스 시트(CASE_SHEETS)는 이 레코드를
// 참조만 하고 값을 복제하지 않는다 — 라이브러리가 근거의 단일 출처다.
import type { CitationRecord } from '@/types';

export const CITATION_LIBRARY: CitationRecord[] = [
  {
    id: 'cit_001',
    grade: 'A',
    title: '출입국관리법 시행규칙 · 연장 제출서류 별표',
    source: '국가법령정보센터',
    updatedAt: '2026.07.01',
    status: 'official',
  },
  {
    id: 'cit_002',
    grade: 'A',
    title: '외국인근로자고용법 시행령 · 고용변동 신고',
    source: '국가법령정보센터',
    updatedAt: '2026.06.28',
    status: 'official',
  },
  {
    id: 'cit_003',
    grade: 'A',
    title: '출입국관리법 제25조 · 체류기간 연장허가',
    source: '국가법령정보센터',
    updatedAt: '2026.07.01',
    status: 'official',
  },
  {
    id: 'cit_004',
    grade: 'B',
    title: '고용24 · 외국인근로자 고용변동 신고 절차',
    source: '고용24',
    updatedAt: '2026.06.20',
    status: 'official',
  },
  {
    id: 'cit_007',
    grade: 'A',
    title: '출입국관리법 시행규칙 · 경과 시 조치',
    source: '국가법령정보센터',
    updatedAt: '2026.07.01',
    status: 'official',
  },
  {
    id: 'cit_009',
    grade: 'B',
    title: '하이코리아 · 체류기간 연장 민원 안내',
    source: 'HiKorea',
    updatedAt: '2026.04.02',
    status: 'review_needed',
  },
  {
    id: 'cit_011',
    grade: 'B',
    title: 'KOSHA · 외국인 근로자 다국어 안전 안내',
    source: '안전보건공단',
    updatedAt: '2025.11.14',
    status: 'stale',
  },
  {
    id: 'cit_014',
    grade: 'E',
    title: '내부 승인 템플릿 · 서류요청 (VN/KR/ID/MN)',
    source: '내부 · 김담당',
    updatedAt: '2026.07.05',
    status: 'internal',
  },
  {
    id: 'cit_021',
    grade: 'E',
    title: '내부 체크리스트 · 행정사 전달 패키지 구성',
    source: '내부 · 김담당',
    updatedAt: '2026.07.02',
    status: 'review_needed',
  },
];

const BY_ID = new Map(CITATION_LIBRARY.map((record) => [record.id, record]));

// 케이스 시트가 라이브러리 레코드를 참조할 때 쓰는 헬퍼 — 없는 id는 픽스처 오류이므로 즉시 throw.
export function libCitation(id: string): CitationRecord {
  const record = BY_ID.get(id);
  if (!record) throw new Error(`근거 라이브러리에 없는 id: ${id}`);
  return record;
}
