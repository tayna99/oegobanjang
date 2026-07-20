import { useSessionStore } from '@/stores/sessionStore';
import type { CitationRecord } from '@/types';
import { apiFetch } from './client';

// GET /api/v1/citations 응답 DTO(backend/app/schemas/citation.py CitationOut, snake_case) — SD-3.
// F등급은 서버가 애초에 저장하지 않으므로(evidence_ingest.upsert_citations) 여기 나타나지 않는다.
export interface CitationDto {
  id: string;
  grade: string;
  title: string;
  source: string;
  status: string;
  updated_at: string;
}

function toCitationRecord(dto: CitationDto): CitationRecord {
  return {
    id: dto.id,
    grade: dto.grade as CitationRecord['grade'],
    title: dto.title,
    source: dto.source,
    status: dto.status as CitationRecord['status'],
    updatedAt: dto.updated_at,
  };
}

// citations.py는 cases.py/threads.py와 달리 company_id를 토큰에서 묵시적으로 derive하지 않고
// 쿼리 파라미터로 명시 요구한다(멀티테넌트 전환 후 회사 선택 UI를 염두에 둔 설계) — 호출부가
// sessionStore.companyId를 넘긴다.
export async function fetchCitationLibrary(companyId: string): Promise<CitationRecord[]> {
  const token = useSessionStore.getState().token ?? undefined;
  const dtos = await apiFetch<CitationDto[]>(`/api/v1/citations?company_id=${encodeURIComponent(companyId)}`, { token });
  return dtos.map(toCitationRecord);
}
