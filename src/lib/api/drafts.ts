import { useSessionStore } from '@/stores/sessionStore';
import { apiFetch } from './client';

// GET /api/v1/cases/{case_id}/draft 응답 DTO(backend/app/schemas/draft.py DraftOut, snake_case) — SD-5.
// revised_text(mock DraftFixture의 단일 "부드러운 톤 제안")는 서버에 없다 — draft_variants.is_revised가
// 언어별 행으로 이미 그 개념을 담고 있어 여기서는 있는 그대로 노출한다(필터링은 화면 몫,
// DraftPage.tsx 참고).
export interface DraftLangVariantDto {
  lang: string;
  text: string;
  is_revised: boolean;
}

export interface DraftDto {
  draft_id: string;
  channel: string;
  purpose: string;
  status: string;
  langs: DraftLangVariantDto[];
}

export interface DraftLangVariant {
  lang: string;
  label: string;
  text: string;
  isRevised: boolean;
}

export interface Draft {
  draftId: string;
  channel: string;
  purpose: string; // mock DraftFixture.title과 같은 개념(DB 컬럼명은 purpose) — DraftPage가 제목으로 쓴다.
  status: string;
  langs: DraftLangVariant[];
}

// mocks/drafts.ts DraftLangVariant.label 표기를 그대로 승계 — 서버는 언어 코드만 내려주므로
// 여기서 사람이 읽는 라벨로 변환한다(db/schema.sql draft_variants.lang CHECK: ko/vi/id/en).
const LANG_LABELS: Record<string, string> = {
  ko: '한국어',
  vi: '베트남어',
  id: '인도네시아어',
  en: '영어',
};

function toDraft(dto: DraftDto): Draft {
  return {
    draftId: dto.draft_id,
    channel: dto.channel,
    purpose: dto.purpose,
    status: dto.status,
    langs: dto.langs.map((item) => ({
      lang: item.lang,
      label: LANG_LABELS[item.lang] ?? item.lang,
      text: item.text,
      isRevised: item.is_revised,
    })),
  };
}

export async function fetchCaseDraft(caseId: string): Promise<Draft> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<DraftDto>(`/api/v1/cases/${caseId}/draft`, { token });
  return toDraft(dto);
}
