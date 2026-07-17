import { useSessionStore } from '@/stores/sessionStore';
import type { EvidenceEvent, EvidenceType } from '@/types';
import { apiFetch } from './client';

// GET/POST /api/v1/evidence 어댑터(R2.5) — backend/app/schemas/evidence.py의 EvidenceEventOut
// 그대로(snake_case). docs/DB_SCHEMA.md §8 매핑 계약: hash=input_hash, evidenceRef='#'+event_no,
// actor=actor_display.
export interface EvidenceEventDto {
  id: string;
  company_id: string;
  event_no: number;
  type: string;
  at: string;
  case_id: string | null;
  summary: string;
  input_hash: string | null;
  actor_display: string | null;
}

export function toEvidenceEvent(dto: EvidenceEventDto): EvidenceEvent {
  return {
    id: dto.id,
    type: dto.type as EvidenceType,
    at: dto.at,
    caseId: dto.case_id ?? undefined,
    hash: dto.input_hash ?? undefined,
    summary: dto.summary,
    actor: dto.actor_display ?? undefined,
    evidenceRef: `#${dto.event_no}`,
  };
}

// evidenceStore.append()가 real 모드에서 호출하는 범용 기록 경로 — action_id/approval_id/run_id는
// 보내지 않는다(백엔드 서비스가 참조 도메인이 아직 실제 행을 보장 못 하는 경우가 많아 거부하므로,
// 여기서부터 그 필드들을 만들어 보내지 않는다. src/stores/evidenceStore.ts 주석 참조).
export async function createEvidenceEvent(event: Pick<EvidenceEvent, 'type' | 'caseId' | 'summary'>): Promise<void> {
  const token = useSessionStore.getState().token ?? undefined;
  await apiFetch<EvidenceEventDto>('/api/v1/evidence', {
    method: 'POST',
    token,
    body: { type: event.type, case_id: event.caseId ?? null, summary: event.summary ?? '' },
  });
}

export async function fetchEvidence(): Promise<EvidenceEvent[]> {
  const token = useSessionStore.getState().token ?? undefined;
  const dtos = await apiFetch<EvidenceEventDto[]>('/api/v1/evidence', { token });
  return dtos.map(toEvidenceEvent);
}
