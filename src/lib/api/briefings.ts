import type { CaseCard } from '@/types';
import { type CaseDto, toCaseCard } from './cases';
import { ApiError, apiFetch } from './client';

// GET /api/v1/briefings/latest 응답 DTO(backend/app/schemas/briefing.py) — cases는 cases.ts의
// CaseDto/toCaseCard를 그대로 재사용한다(백엔드가 이미 CaseOut을 재사용하는 것과 대칭).
export interface BriefingDto {
  id: string;
  briefing_date: string;
  generated_at: string;
  cases: CaseDto[];
}

export interface Briefing {
  briefingId: string;
  briefingDate: string;
  generatedAt: string;
  // briefing_items rank 순으로 서버가 이미 정렬해 내려준다.
  cases: CaseCard[];
}

function toBriefing(dto: BriefingDto): Briefing {
  return {
    briefingId: dto.id,
    briefingDate: dto.briefing_date,
    generatedAt: dto.generated_at,
    cases: dto.cases.map(toCaseCard),
  };
}

// 아직 그날의 브리핑이 생성되지 않은 경우 백엔드가 404를 반환한다 — 예외로 던지지 않고 null로
// 변환해, 호출부가 "브리핑 없음"과 "요청 실패"를 구분해 처리하지 않아도 되게 한다(빈 상태 화면).
export async function fetchLatestBriefing(): Promise<Briefing | null> {
  try {
    return toBriefing(await apiFetch<BriefingDto>('/api/v1/briefings/latest'));
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}
