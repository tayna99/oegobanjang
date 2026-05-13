export type MobileDemoStep = "briefing" | "detail" | "process" | "draft" | "done";

export const demoTask = {
  worker: {
    name: "Nguyen Van A",
    displayName: "Nguyen V.",
    nationality: "베트남",
    visaType: "E-9",
    language: "베트남어",
    contactChannel: "Zalo",
    worksite: "화성 2공장",
    line: "조립라인",
  },
  dDay: 30,
  expiryDate: "2026.06.20",
  contractEndDate: "2026.07.01",
  missingDocuments: ["표준근로계약서 사본", "여권 사본"],
  previousRecord: "3일 전 요청 이력 있음",
  workLogId: "4789",
  draft: {
    vi: "Xin chào Nguyen, vui lòng gửi bản sao hợp đồng lao động tiêu chuẩn và hộ chiếu. Cảm ơn bạn.",
    ko: "안녕하세요 Nguyen 씨, 표준근로계약서 사본과 여권 사본을 보내주세요. 감사합니다.",
    politeVi:
      "Xin chào anh Nguyen, để chuẩn bị hồ sơ gia hạn thời gian lưu trú, vui lòng gửi giúp chúng tôi bản sao hợp đồng lao động tiêu chuẩn và bản sao hộ chiếu. Cảm ơn anh.",
    politeKo:
      "안녕하세요 Nguyen 씨. 체류기간 연장 준비를 위해 표준근로계약서 사본과 여권 사본을 보내주시면 감사하겠습니다. 감사합니다.",
  },
};
