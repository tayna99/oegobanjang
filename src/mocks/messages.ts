// 메시지 스레드 + M6 응답 해석 — reference/specs/1단계_화면상태스펙_M1-M9_v1.md §M6, 탭별기획 §3(2.2).
// 디자인 미포함(블루프린트 §9-A) — 2b 검토 패턴 재사용. 목록엔 근로자 원문 미노출(GOTCHAS §3),
// 원문은 스레드 내부에서만. M6: 응답 도착 시 원문 → KR 요약 → 상태 업데이트 제안(담당자 확인 필요).

export type MessageSender = 'worker' | 'manager' | 'agent';

export interface ThreadMessage {
  id: string;
  sender: MessageSender;
  lang?: 'ko' | 'vi' | 'id' | 'en'; // 근로자 메시지 원문 언어
  text: string;
  at: string; // "오늘 10:12" 데모 고정값
}

// M6 응답 해석 — 근로자 회신에 대한 에이전트 해석. isFinal:false면 담당자 확인 후 상태 반영.
export interface ResponseInterpretation {
  originalLang: 'vi' | 'id' | 'en';
  originalText: string; // 근로자 원문(스레드 내부에서만 노출)
  koSummary: string; // 한국어 요약
  proposal: string; // 상태 업데이트 제안
  isFinal: boolean; // false = 담당자 확인 필요
}

export interface MessageThread {
  threadId: string; // = caseId
  caseId: string;
  workerName: string;
  team: string;
  channel: string; // 'Zalo' | 'SMS'
  listLabel: string; // 목록 표시용 상태 라벨(원문 아님) — GOTCHAS 원문 미노출
  hasResponse: boolean; // 응답 도착(해석 필요) 배지
  messages: ThreadMessage[];
  interpretation?: ResponseInterpretation; // 있으면 M6 해석 카드
}

export const MESSAGE_THREADS: Record<string, MessageThread> = {
  tranCase: {
    threadId: 'tranCase',
    caseId: 'tranCase',
    workerName: 'Tran Thi H.',
    team: '품질팀',
    channel: 'Zalo',
    listLabel: '응답 도착 · 해석 필요',
    hasResponse: true,
    messages: [
      {
        id: 'tran-out-1',
        sender: 'manager',
        text: '안녕하세요 Tran 씨, 계약서 사본과 여권 사본 제출 부탁드립니다.',
        at: '어제 15:20',
      },
      {
        id: 'tran-in-1',
        sender: 'worker',
        lang: 'vi',
        text: 'Hợp đồng công ty giữ, hộ chiếu mai em nộp ạ.',
        at: '오늘 10:12',
      },
    ],
    interpretation: {
      originalLang: 'vi',
      originalText: 'Hợp đồng công ty giữ, hộ chiếu mai em nộp ạ.',
      koSummary: '계약서는 회사가 보관 중이며, 여권 사본은 내일 제출하겠다는 응답입니다.',
      proposal: '여권 사본 상태를 "제출 예정(내일)"으로 갱신하고, 계약서는 회사 보관으로 확인 처리할까요?',
      isFinal: false,
    },
  },
  nguyen: {
    threadId: 'nguyen',
    caseId: 'nguyen',
    workerName: 'Nguyen Van A',
    team: '제조1팀',
    channel: 'Zalo',
    listLabel: '서류 요청 발송 대기 (승인 전)',
    hasResponse: false,
    messages: [
      {
        id: 'nguyen-draft-note',
        sender: 'agent',
        text: '서류요청 초안이 준비됐습니다. 승인 후 발송됩니다.',
        at: '오늘 07:58',
      },
    ],
  },
};

export function threadFor(threadId: string | undefined): MessageThread | undefined {
  return threadId ? MESSAGE_THREADS[threadId] : undefined;
}

export const THREAD_LIST: MessageThread[] = Object.values(MESSAGE_THREADS);
