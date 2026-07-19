// 근로자 응답 링크(R3.2 프론트 절반) 목 데이터 — reference/design-system/design-briefs/
// 근로자_응답링크_브리프.md + docs/DESIGN_SYNC_AUDIT_2026-07-17.md §3. 목업 스크립트의 vi/ko
// 카피 사전을 그대로 옮긴다(창작 금지 원칙). 발신 메시지 내용은 이 화면 전용 표시값이지
// mocks/threads.ts의 실제 메시지와는 별개다(응답 링크는 채널 인바운드 지점이라 스레드에
// 이미 있는 메시지와 물리적으로 대응할 필요가 없다 — 실제 서비스에서도 토큰이 발급되는
// 시점의 메시지 내용을 별도로 들고 있는 게 정상 계약).
export type ResponseLinkState = 'active' | 'expired' | 'already_replied';

export interface ResponseLinkCopy {
  serviceName: string;
  fromLabel: string;
  senderName: string;
  senderCompany: string;
  messageBody: string;
  docListTitle: string;
  docList: string;
  replyLabel: string;
  presets: string[];
  freeLabel: string;
  optional: string;
  freePlaceholder: string;
  reviewNotice: string;
  submitLabel: string;
  doneTitle: string;
  doneDesc: string;
  yourReply: string;
  lockNotice: string;
}

export const RESPONSE_LINK_COPY: Record<'vi' | 'ko', ResponseLinkCopy> = {
  vi: {
    serviceName: 'Ngoại Cao Ban Trưởng',
    fromLabel: 'Tin nhắn từ người quản lý',
    senderName: 'Quản lý Kim Min-su',
    senderCompany: 'Greenfood',
    messageBody:
      'Anh Nguyen Van A, để gia hạn thời gian lưu trú, vui lòng chuẩn bị các giấy tờ dưới đây trước ngày 24-07.',
    docListTitle: 'Giấy tờ cần chuẩn bị',
    docList: '1. Hộ chiếu (bản gốc) · 2. Giấy xác nhận làm việc',
    replyLabel: 'Chọn câu trả lời',
    presets: ['Tôi đã xác nhận', 'Vui lòng gửi lại', 'Tôi có câu hỏi'],
    freeLabel: 'Nội dung thêm',
    optional: 'Không bắt buộc',
    freePlaceholder: 'Nhập nội dung (không bắt buộc)',
    reviewNotice: 'Câu trả lời sẽ được phản ánh sau khi người quản lý xác nhận.',
    submitLabel: 'Gửi câu trả lời',
    doneTitle: 'Đã gửi câu trả lời',
    doneDesc: 'Câu trả lời sẽ được phản ánh sau khi người quản lý xác nhận.',
    yourReply: 'Câu trả lời của bạn',
    lockNotice: 'Không thể gửi lại câu trả lời.',
  },
  ko: {
    serviceName: '외고반장',
    fromLabel: '담당자가 보낸 메시지',
    senderName: '김민수 담당자',
    senderCompany: '그린푸드 제조',
    messageBody: 'Nguyen Van A님, 체류기간 연장을 위해 아래 서류를 7월 24일까지 준비해 주세요.',
    docListTitle: '준비할 서류',
    docList: '1. 여권 (원본) · 2. 재직 확인서',
    replyLabel: '답변 선택',
    presets: ['확인했습니다', '다시 보내주세요', '질문이 있습니다'],
    freeLabel: '추가 내용',
    optional: '선택 사항',
    freePlaceholder: '내용 입력 (선택 사항)',
    reviewNotice: '답변은 담당자 확인 후 반영됩니다.',
    submitLabel: '답변 보내기',
    doneTitle: '답변을 보냈습니다',
    doneDesc: '답변은 담당자 확인 후 반영됩니다.',
    yourReply: '내 답변',
    lockNotice: '답변을 다시 보낼 수 없습니다.',
  },
};

export interface ResponseLinkFixture {
  token: string;
  threadId: string;
  lang: 'vi'; // 목업 카피 사전이 vi/ko만 확보돼 있다 — 다른 모국어는 카피가 갖춰질 때 추가
  state: ResponseLinkState;
}

const FIXTURES: Record<string, ResponseLinkFixture> = {
  'nguyen-stay-extension': { token: 'nguyen-stay-extension', threadId: 'nguyen', lang: 'vi', state: 'active' },
  'tran-doc-request': { token: 'tran-doc-request', threadId: 'tran', lang: 'vi', state: 'already_replied' },
  'expired-demo': { token: 'expired-demo', threadId: 'nguyen', lang: 'vi', state: 'expired' },
};

// 무효 토큰(무효 상태)은 이 함수가 undefined를 반환하는 것으로 표현한다 — 링크 없음과
// 만료됨을 구분하되, 존재 자체는 어느 쪽도 그 이상 정보를 주지 않는다(감사 §3 가드레일).
export function responseLinkFor(token: string | undefined): ResponseLinkFixture | undefined {
  if (!token) return undefined;
  return FIXTURES[token];
}
