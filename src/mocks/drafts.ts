// DRAFT 레지스트리 이식 — reference/prototype_v3.html의 DRAFT(§618)를
// 1단계 스펙 §M3 컴포넌트 계약으로 정규화 (M0.5, docs/SPEC_INDEX.md 이식표: KR/VN/EN + revised).
// 스펙 §M3의 LangToggle은 'ko'|'vi'|'id'만 정의하지만 이식표가 "EN"도 명시해
// 로컬 타입에 'en'을 유지한다(2.5.4b 로스터 치환 후 현재 en 초안은 없음).

export type DraftLangCode = 'ko' | 'vi' | 'en';

export interface DraftLangVariant {
  lang: DraftLangCode;
  label: string; // v3 세그먼트 라벨 원문: '한국어' | '베트남어' | '영어'
  text: string;
}

export interface DraftScenario {
  type: 'positive' | 'question' | 'delayed'; // ExpectedResponseCard.type
  label: string;
  description: string;
}

export interface DraftFixture {
  draftKey: string; // v3 DRAFT 레지스트리 키 — src/mocks/runs.ts RUN_CONFIGS.runKey와 연결
  caseId: string;
  title: string;
  channel: string; // 'Zalo' | 'SMS'
  langs: DraftLangVariant[];
  revisedText: string; // [수정 요청] 적용 후 텍스트 (v3 revised)
}

function scenario(label: string, description: string): DraftScenario {
  let type: DraftScenario['type'] = 'positive';
  if (label.includes('지연')) type = 'delayed';
  else if (label.includes('질문') || label.includes('문의') || label.includes('변경')) type = 'question';
  return { type, label, description };
}

export const DRAFTS: Record<string, DraftFixture> = {
  nguyen: {
    draftKey: 'nguyen',
    caseId: 'nguyen',
    title: '서류 요청 메시지',
    channel: 'Zalo',
    langs: [
      {
        lang: 'ko',
        label: '한국어',
        text: '안녕하세요 Nguyen 씨,\n체류기간 연장 준비를 위해 아래 서류가 필요합니다.\n\n· 표준근로계약서 사본\n· 여권 사본\n\n가능하면 2일 이내에 보내주세요.\n제출하신 서류는 고용 및 체류 관련 행정 절차에만 사용됩니다.\n\n감사합니다.',
      },
      {
        lang: 'vi',
        label: '베트남어',
        text: 'Xin chào Nguyen,\nđể chuẩn bị gia hạn thời gian lưu trú, vui lòng gửi các giấy tờ sau.\n\n· Bản sao hợp đồng lao động tiêu chuẩn\n· Bản sao hộ chiếu\n\nVui lòng gửi trong vòng 2 ngày nếu có thể.\nGiấy tờ chỉ được dùng cho thủ tục hành chính về việc làm và lưu trú.\n\nCảm ơn bạn.',
      },
    ],
    revisedText:
      '안녕하세요 Nguyen 씨, 잘 지내고 계신가요.\n체류기간 연장을 준비하고 있어 서류 두 가지를 부탁드리려고 합니다.\n\n· 표준근로계약서 사본\n· 여권 사본\n\n바쁘시겠지만 이번 주 안에 보내주시면 큰 도움이 됩니다.\n제출하신 서류는 고용 및 체류 관련 행정 절차에만 사용됩니다.\n\n항상 감사합니다.',
  },
  tranReminder: {
    draftKey: 'tranReminder',
    caseId: 'tranCase',
    title: '리마인드 초안',
    channel: 'Zalo',
    langs: [
      {
        lang: 'ko',
        label: '한국어',
        text: '안녕하세요 Tran 씨,\n어제 말씀하신 여권 사본을 오늘 보내주실 수 있을까요.\n계약 관련 준비에 필요합니다.\n\n감사합니다.',
      },
      {
        lang: 'vi',
        label: '베트남어',
        text: 'Chào anh Tran,\nanh có thể gửi bản sao hộ chiếu hôm nay như đã nói không ạ.\nCần cho việc chuẩn bị hợp đồng.\n\nCảm ơn anh.',
      },
    ],
    revisedText:
      '안녕하세요 Tran 씨, 바쁘신데 죄송합니다.\n어제 말씀해주신 여권 사본을 편하실 때 보내주시면 감사하겠습니다.\n계약 관련 준비에 필요해서요.\n\n고맙습니다.',
  },
};

// caseId → 초안 조회 단일 출처(코드리뷰 D/E 교정: 4개 화면이 각자 Object.values(DRAFTS).find를
// 복제·매 렌더 재스캔하던 것을 여기 인덱스로 통합).
const DRAFTS_BY_CASE: Record<string, DraftFixture> = Object.fromEntries(
  Object.values(DRAFTS).map((draft) => [draft.caseId, draft]),
);

export function draftForCase(caseId: string | undefined): DraftFixture | undefined {
  return caseId ? DRAFTS_BY_CASE[caseId] : undefined;
}

export const DRAFT_SCENARIOS: Record<string, DraftScenario[]> = {
  nguyen: [
    scenario('긍정 응답', '서류 수신 후 검토 자료에 반영'),
    scenario('추가 질문', '서류 형식 기준 재안내'),
    scenario('응답 지연', '2일 뒤 리마인드 제안'),
  ],
  tranReminder: [
    scenario('긍정 응답', '여권 수신 후 상태 갱신'),
    scenario('일정 변경', '제출 예정일 갱신'),
    scenario('응답 지연', '추가 리마인드 판단'),
  ],
};
