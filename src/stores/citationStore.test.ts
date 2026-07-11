import { describe, expect, it } from 'vitest';
import { CITATION_LIBRARY, libCitation } from '@/mocks/citations';
import { CASE_SHEETS } from '@/mocks/fixtures';
import { citationKpis, linkedCaseCount, usableCitations } from './citationStore';
import type { CitationRecord } from '@/types';

describe('근거 라이브러리 (2.5.4b, 디자인 §3c)', () => {
  it('KPI는 레코드에서 파생된다 (ROADMAP 2.5.5 DoD: KPI=스토어 파생값)', () => {
    const kpis = citationKpis(CITATION_LIBRARY);
    expect(kpis.total).toBe(CITATION_LIBRARY.length);
    expect(kpis.official).toBe(CITATION_LIBRARY.filter((r) => r.grade === 'A' || r.grade === 'B').length);
    expect(kpis.stale).toBe(1); // cit_011 KOSHA
    expect(kpis.fresh).toBe(kpis.total - kpis.stale);
  });

  it('연계 케이스 수는 케이스 시트 참조에서 파생된다', () => {
    const sheets = Object.values(CASE_SHEETS);
    // cit_004(고용변동 신고 절차)는 siti·tranCase 두 케이스가 참조한다.
    expect(linkedCaseCount('cit_004', sheets)).toBe(2);
    // cit_011(KOSHA stale)은 어떤 케이스도 참조하지 않는다.
    expect(linkedCaseCount('cit_011', sheets)).toBe(0);
  });

  it('케이스 시트의 근거는 전부 라이브러리 레코드 참조다(id 보유)', () => {
    for (const sheet of Object.values(CASE_SHEETS)) {
      for (const citation of sheet.citations) {
        expect(citation.id, `${sheet.caseId}의 근거에 id 없음`).toBeDefined();
        expect(libCitation(citation.id as string).title).toBe(citation.title);
      }
    }
  });
});

describe('가드레일 — F등급(합성 데이터)은 근거로 사용 불가 (§3c 각주 비준)', () => {
  const fake: CitationRecord = {
    id: 'cit_f01',
    grade: 'F',
    title: '합성 데이터 예시',
    source: '테스트',
    updatedAt: '2026.07.11',
    status: 'internal',
  };

  it('usableCitations가 F등급을 제외한다 — citation-0 잠금 판정에 세지 않는다', () => {
    expect(usableCitations([fake])).toHaveLength(0);
    expect(usableCitations([fake, libCitation('cit_001')])).toHaveLength(1);
  });
});
