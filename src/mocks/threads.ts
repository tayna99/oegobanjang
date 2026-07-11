// THREADS 이식 — reference/prototype_v3.html의 메시지 탭·스레드 마크업을
// src/types.ts MessageThread/Interpretation으로 정규화 (2.2, docs/MESSAGING_CHANNELS.md §4 이식표).
// 원본 라인 근처: 271행(Tran 카드 gotoThread('tran')), 316~334행(메시지 탭 리스트 — msgNsub/msgTsub/msgBsub),
// 905~932행(gotoThread 스레드 렌더), 933~946행(interpHTML/interpDoneHTML), 947~954행(confirmInterp),
// 550행·580~582행(CASE_SHEETS 활동 로그 acts — tranCase 응답 도착·해석 완료).
//
// evidenceRef 주의: v3 913행의 Tran 발신 버블 메타는 "판단 기록 #4741"이지만, #4741은 이미
// src/mocks/fixtures.ts CASE_SHEETS.nguyen.activity의 "1차 서류 요청" 런과 겹친다(판단 기록 번호는
// 케이스를 넘나들어도 유일해야 한다). 그래서 여기서는 Tran 발신 메시지의 evidenceRef만 #4742로
// 바꿔 쓴다. #4791(해석 확인)·#4796(리마인드) 등 다른 번호는 v3·기존 mock과 충돌이 없어 그대로 둔다.
import type { Interpretation, MessageThread } from '@/types';

const TRAN_INTERPRETATION: Interpretation = {
  interpretationId: 'tran-interp-1',
  threadId: 'tran',
  caseId: 'tranCase',
  // v3 936행 <p> 원문(볼드 태그만 제거) — 근로자 원문 문장이 아니라 이미 한국어 요약이므로 그대로 옮긴다.
  summaryKo: '표준근로계약서는 회사가 보관 중이라고 답했습니다. 여권 사본은 내일 제출 예정입니다.',
  confidence: 'high',
  updates: [
    // v3 937행 — 표준근로계약서: 누락 → 회사 확인 필요
    { field: '표준근로계약서', from: '누락', to: '회사 확인 필요', badgeTone: 'warning' },
    // v3 938행 — 여권 사본: 누락 → 제출 예정 · 내일
    { field: '여권 사본', from: '누락', to: '제출 예정 · 내일', badgeTone: 'warning' },
  ],
  recommendedActions: [
    {
      // v3 939행 "추천 → 회사 보관 계약서 확인"을 NextActionRef로 승격 (문자열 라벨 분기 금지)
      action: {
        actionId: 'tranCase-interp-confirm-contract',
        label: '회사 보관 계약서 확인',
        state: 'ready',
        requiresApproval: false,
        kind: 'confirm',
      },
      reason: '표준근로계약서를 회사가 보관 중이라고 응답했습니다',
    },
  ],
  isFinal: false, // 담당자 확인 전 — GLOSSARY.md "isFinal:false 필수"
  // v3 952행 addEv 호출의 summary 원문 — Evidence summary와 동일 문장이어야 한다(타입 주석 규칙)
  confirmedSummary: 'Tran 응답 해석 확인 — 서류 상태 2건 갱신',
  // v3 945~946행 interpDoneHTML() 원문
  confirmedCardText: '상태 반영 완료 — 계약서 회사 확인 · 여권 제출 대기 (판단 기록 #4791)',
  evidenceRef: '#4791',
};

export const THREADS: MessageThread[] = [
  {
    threadId: 'nguyen',
    workerRef: { displayName: 'Nguyen V.', nationality: '베트남', maskLevel: 'masked' },
    channel: 'zalo',
    channelLabel: 'Zalo',
    draftCaseId: 'nguyen', // 케이스는 이미 있지만 스레드에는 아직 발송된 메시지가 없다(초안 단계)
    messages: [],
    interpretationStatus: 'none',
    preview: '서류 요청 초안 — 표준근로계약서·여권 사본', // v3 319행 msgNsub 원문
    timeLabel: '오늘', // v3 320행
  },
  {
    threadId: 'tran',
    workerRef: { displayName: 'Tran T.H.', nationality: '베트남', maskLevel: 'masked' },
    channel: 'zalo',
    channelLabel: 'Zalo',
    caseId: 'tranCase',
    messages: [
      {
        messageId: 'tran-msg-out-1',
        threadId: 'tran',
        direction: 'out',
        channel: 'zalo',
        // v3 912행 원문 그대로 — 스레드 내부 렌더 전용
        body: 'Chào anh Tran,\nhợp đồng của anh sẽ kết thúc vào ngày 18.8.\nVui lòng xác nhận bản sao hợp đồng lao động và hộ chiếu.',
        lang: 'vi',
        at: '2026-07-01T09:20:00.000Z', // v3 911행 "7월 1일" · 913행 "09:20"
        deliveryStatus: 'sent',
        evidenceRef: '#4742', // #4741 충돌 회피 — 파일 머리말 주석 참고
        caseId: 'tranCase',
      },
      {
        messageId: 'tran-msg-in-1',
        threadId: 'tran',
        direction: 'in',
        channel: 'zalo',
        // v3 915행 원문 그대로 — 목록 미리보기·evidence 요약에는 노출 금지(GOTCHAS §3)
        body: 'Hợp đồng lao động thì công ty đang giữ ạ.\nHộ chiếu ngày mai tôi sẽ gửi bản sao.',
        lang: 'vi',
        at: '2026-07-04T10:12:00.000Z', // v3 914행 "오늘" · 916행 "10:12"
        caseId: 'tranCase',
      },
    ],
    interpretation: TRAN_INTERPRETATION,
    interpretationStatus: 'pending_review',
    preview: '응답 도착 — AI 해석 준비됨 · 담당자 확인 필요', // v3 325행 msgTsub 원문
    timeLabel: '10:12', // v3 326행
  },
  {
    threadId: 'bayar',
    workerRef: { displayName: 'Bayar M.', nationality: '몽골', maskLevel: 'masked' },
    channel: 'sms',
    channelLabel: 'SMS',
    caseId: 'bayar',
    messages: [
      {
        messageId: 'bayar-msg-out-1',
        threadId: 'bayar',
        direction: 'out',
        channel: 'sms',
        // v3 925행 원문 그대로
        body: 'Сайн байна уу Bayar,\nэрүүл мэндийн үзлэгийн товыг баталгаажуулна уу.\n(건강검진 일정 확인 요청)',
        lang: 'mn',
        at: '2026-07-03T15:40:00.000Z', // v3 924행 "어제" · 926행 "15:40"
        deliveryStatus: 'sent',
        evidenceRef: '#4720', // v3 926행 "판단 기록 #4720"
        caseId: 'bayar',
      },
    ],
    interpretationStatus: 'none',
    preview: '건강검진 일정 안내 — 발송 승인 완료 · 응답 대기', // v3 331행 msgBsub 원문
    timeLabel: '어제', // v3 332행
    reminderScheduledLabel: '리마인드 7.6 예정',
  },
];

// caseId → threadId 매핑. Tran은 케이스(tranCase)와 스레드(tran) 식별자가 달라 매핑이 꼭 필요하고,
// Nguyen은 케이스가 이미 있지만 스레드는 draftCaseId로만 연결돼 있어(위 THREADS 참고) 같은
// 함수로 찾을 수 있도록 포함한다. Bayar는 caseId와 threadId가 둘 다 'bayar'이지만, 우연히 같은
// 값일 뿐 이 함수가 보장하는 계약은 아니므로 필요해지면 표에 추가한다.
const CASE_ID_TO_THREAD_ID: Record<string, string> = {
  tranCase: 'tran',
  nguyen: 'nguyen',
};

export function threadIdForCase(caseId: string): string | undefined {
  return CASE_ID_TO_THREAD_ID[caseId];
}
