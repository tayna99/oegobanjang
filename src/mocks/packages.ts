// 행정사 검토 패키지 — reference/design-system/외고반장 PC.dc.html 관제형 §2d(1178~1341행) 이식(2.4).
// fixtures.ts가 "PKG는 M2.4에서 이식"이라 미뤄둔 데이터 모델. Batbayar(기한 경과) 케이스 구동.
// 외국인등록번호는 마스킹 값만 저장(원문 없음). 근거는 라이브러리 cit_* 참조.
import { libCitation } from './citations';
import type { Citation } from '@/types';

export interface PackageItem {
  key: string;
  label: string;
  note?: string; // "(PII 마스킹)", "(2건)" 등 보조 표기
  defaultOn: boolean;
}

export interface PackageDocSection {
  heading: string;
  lines: string[]; // 각 줄은 마스킹 완료 텍스트(원문 PII 없음)
}

export interface HandoffPackage {
  packageId: string; // = caseId
  workerName: string;
  eyebrow: string; // "케이스 · Batbayar E. · 체류기간 만료 경과"
  severityLabel: string; // "CRITICAL · D+2"
  statusLabel: string; // "승인 대기"
  recipient: string; // 수신 행정사무소
  senderLine: string; // 발신
  createdAt: string;
  recordRef: string; // 판단 기록 #·trace
  items: PackageItem[];
  sections: PackageDocSection[]; // 검토 요청서 본문(포함 항목 켜짐에 따라 노출)
  citations: Citation[]; // 근거 각주(cit_* 참조)
  exportHistory: { at: string; kind: string; actor: string; ref: string; hash: string }[];
}

// 고정 문구 — 디자인 §2d 워터마크·요청 사항·푸터(글자 하나도 바꾸지 않는다).
export const PACKAGE_WATERMARK = '내부 검토용 초안 — 승인 전 외부 전달 금지';
export const PACKAGE_REQUEST_BODY =
  '체류기간 경과에 따른 조치 절차 검토와 보완 서류 확인을 요청드립니다. 본 문서는 가능/불가능 판단을 포함하지 않으며, 최종 판단은 행정사 검토에 따릅니다.';
export const PACKAGE_EXPORT_FOOTER = '승인 전에는 외부 발송·전달이 차단됩니다.';

export const HANDOFF_PACKAGES: Record<string, HandoffPackage> = {
  batbayar: {
    packageId: 'batbayar',
    workerName: 'Batbayar E.',
    eyebrow: '케이스 · Batbayar E. · 체류기간 만료 경과',
    severityLabel: 'CRITICAL · D+2',
    statusLabel: '승인 대기',
    recipient: '김앤리 행정사무소',
    senderLine: '그린푸드 제조 · 김담당',
    createdAt: '2026-07-06',
    recordRef: '#4786 · trace_1038',
    items: [
      { key: 'summary', label: '케이스 요약', defaultOn: true },
      { key: 'worker', label: '근로자 정보', note: '(PII 마스킹)', defaultOn: true },
      { key: 'missing', label: '누락 서류 목록', note: '(2건)', defaultOn: true },
      { key: 'reason', label: '체류 경과 사유서 초안', defaultOn: true },
      { key: 'history', label: '이전 승인 이력 요약', defaultOn: false },
    ],
    sections: [
      {
        heading: '1. 케이스 개요',
        lines: [
          '근로자: Batbayar E. (제조2팀 · E-9)',
          '외국인등록번호: ******-*******', // 마스킹 — 원문 저장 안 함(lib/mask.ts 규칙과 동일 형식)
          '체류만료일: 2026-07-04 (D+2 경과)',
          '리스크: CRITICAL · visa_expiry (체류기간 만료 경과)',
        ],
      },
      {
        heading: '2. 누락 서류',
        lines: ['· 고용변동 신고서 초안 (첨부 1)', '· 체류 경과 사유서 초안 (첨부 2)'],
      },
      {
        heading: '3. 요청 사항',
        lines: [PACKAGE_REQUEST_BODY],
      },
    ],
    citations: [libCitation('cit_003'), libCitation('cit_007'), libCitation('cit_021')],
    exportHistory: [
      { at: '07/02 14:10', kind: 'PDF', actor: '김담당', ref: 'export_0031', hash: 'sha256:aa72…3c19' },
      { at: '06/28 09:55', kind: '미리보기 링크', actor: '김담당', ref: 'export_0027', hash: 'sha256:5e08…77b4' },
    ],
  },
};

export function packageFor(packageId: string | undefined): HandoffPackage | undefined {
  return packageId ? HANDOFF_PACKAGES[packageId] : undefined;
}
