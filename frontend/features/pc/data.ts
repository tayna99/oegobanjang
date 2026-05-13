export type PcViewKey = "today" | "hiring" | "workers" | "contact" | "cases" | "admin" | "judgment";

export type Tone = "blue" | "green" | "orange" | "red" | "gray" | "purple" | "teal";

export type TodayTaskKind = "doc" | "hiring" | "message";

export type TodayTask = {
  kind: TodayTaskKind;
  title: string;
  target: string;
  worksiteLine: string;
  status: string;
  deadline: string;
  riskLevel: "높음" | "중간" | "낮음";
  owner: string;
  next: string;
  tone: Tone;
  detail: {
    title: string;
    statusBadges: string[];
    subject: string;
    nationality?: string;
    visaType?: string;
    channel?: string;
    language?: string;
    visaExpiryDate?: string;
    contractEndDate?: string;
    why: string;
    prepared: string[];
    missingDocuments?: string[];
    nextActions: string[];
    evidence: string[];
    judgmentRecordId: string;
  };
};

export const company = {
  name: "한별제조",
  location: "경기 화성",
  manager: "김대리",
  role: "인사팀",
};

export const workers = [
  {
    id: "w_nguyen",
    initials: "V",
    name: "Nguyen V.",
    localName: "응우엔 V.",
    nationalityCode: "VN",
    nationality: "베트남",
    visaType: "E-9-1",
    line: "화성 2공장 조립라인",
    visaExpiry: "2026.06.20",
    contractEnd: "2026.07.01",
    dday: "D-30",
    status: "우선 확인",
    statusTone: "orange" as Tone,
    tenure: "2년 7개월",
    docs: ["여", "외", "근", "건"],
    docExtra: "+2",
  },
  {
    id: "w_bayar",
    initials: "B",
    name: "Bayar M.",
    localName: "바야르 M.",
    nationalityCode: "MN",
    nationality: "몽골",
    visaType: "E-9-1",
    line: "B동 도장공정",
    visaExpiry: "2026.05.05",
    contractEnd: "2026.05.05",
    dday: "D+3",
    status: "즉시 확인",
    statusTone: "red" as Tone,
    tenure: "4년 1개월",
    docs: ["여", "외", "근", "건"],
    docExtra: "+1",
  },
  {
    id: "w_tran",
    initials: "T",
    name: "Tran T. H.",
    localName: "쩐 T. H.",
    nationalityCode: "VN",
    nationality: "베트남",
    visaType: "E-9-1",
    line: "A동 조립라인",
    visaExpiry: "2026.09.15",
    contractEnd: "2026.06.22",
    dday: "D-130",
    status: "확인 필요",
    statusTone: "blue" as Tone,
    tenure: "1년 8개월",
    docs: ["여", "외", "근", "건"],
  },
  {
    id: "w_mohammad",
    initials: "M",
    name: "Mohammad I.",
    localName: "모하맛 I.",
    nationalityCode: "BD",
    nationality: "방글라데시",
    visaType: "E-9-1",
    line: "C동 검사라인",
    visaExpiry: "2026.08.12",
    contractEnd: "2026.08.12",
    dday: "D-96",
    status: "확인 필요",
    statusTone: "blue" as Tone,
    tenure: "2년 2개월",
    docs: ["여", "외", "근", "건"],
    docExtra: "+1",
  },
  {
    id: "w_sopheak",
    initials: "S",
    name: "Sopheak S.",
    localName: "소피악 S.",
    nationalityCode: "KH",
    nationality: "캄보디아",
    visaType: "E-9-1",
    line: "B동 도장공정",
    visaExpiry: "2026.07.04",
    contractEnd: "2026.07.04",
    dday: "D-57",
    status: "확인 필요",
    statusTone: "blue" as Tone,
    tenure: "11개월",
    docs: ["여", "외", "근", "건"],
  },
  {
    id: "w_abebe",
    initials: "A",
    name: "Abebe K.",
    localName: "아베베 K.",
    nationalityCode: "ET",
    nationality: "에티오피아",
    visaType: "E-9-1",
    line: "C동 검사라인",
    visaExpiry: "2026.08.30",
    contractEnd: "2026.08.30",
    dday: "D-114",
    status: "정상",
    statusTone: "green" as Tone,
    tenure: "1년 3개월",
    docs: ["여", "외", "근", "건"],
  },
];

export const riskCases = [
  {
    id: "case_001",
    group: "즉시 확인",
    title: "체류만료 초과",
    worker: "Bayar M.",
    nationalityCode: "MN",
    desc: "체류만료일(2026.05.05)이 3일 지났습니다.",
    tone: "red" as Tone,
    actions: ["출입국관리법 제25조", "제94조 벌칙", "행정사 검토용 자료 만들기", "본인 확인 메시지 초안 보기"],
  },
  {
    id: "case_002",
    group: "우선 확인",
    title: "체류만료 임박",
    worker: "Nguyen V.",
    nationalityCode: "VN",
    desc: "체류만료까지 30일 남았습니다. 체류기간 연장 준비 여부를 담당자/전문가가 검토해야 합니다.",
    tone: "orange" as Tone,
    actions: ["출입국관리법 제25조", "체류기간 연장허가 신청 안내", "서류 요청 초안 보기", "체류기간 연장 검토 자료 만들기"],
  },
  {
    id: "case_003",
    group: "우선 확인",
    title: "필수서류 누락",
    worker: "Nguyen V.",
    nationalityCode: "VN",
    desc: "표준근로계약서 사본, 여권 사본 보완이 필요합니다.",
    tone: "orange" as Tone,
    actions: ["외국인근로자 고용 시 보유 서류", "표준근로계약서/여권 사본 요청 초안 보기"],
  },
  {
    id: "case_006",
    group: "우선 확인",
    title: "고용변동 신고기한",
    worker: "사업장 전체",
    desc: "Bayar M. 건의 고용변동 신고기한이 3일 남았습니다.",
    tone: "orange" as Tone,
    actions: ["고용변동 신고서 서식", "신고서 검토 자료 만들기"],
  },
  {
    id: "case_004",
    group: "확인 필요",
    title: "계약·체류 불일치",
    worker: "Tran T. H.",
    nationalityCode: "VN",
    desc: "계약종료일과 체류만료일이 다릅니다. 담당자 확인이 필요합니다.",
    tone: "blue" as Tone,
    actions: ["계약 정보 보기", "검토 메모 작성"],
  },
  {
    id: "case_005",
    group: "확인 필요",
    title: "서류 유효기간 확인",
    worker: "Mohammad I.",
    nationalityCode: "BD",
    desc: "건강진단서와 계약 서류의 최신본 여부를 담당자가 확인해야 합니다.",
    tone: "blue" as Tone,
    actions: ["서류 현황 보기", "확인 메모 작성"],
  },
  {
    id: "case_007",
    group: "확인 필요",
    title: "입국 전 안내 확인",
    worker: "Candidate B",
    desc: "입국 전 안내와 제출 서류 수신 상태 확인이 필요합니다.",
    tone: "blue" as Tone,
    actions: ["후보자 서류 보기", "안내 메시지 초안 보기"],
  },
];

export const todaysTasks: TodayTask[] = [
  {
    kind: "doc",
    title: "체류기간 연장 서류 요청",
    target: "Nguyen V.",
    worksiteLine: "화성 2공장 조립라인",
    status: "우선 확인",
    deadline: "D-30",
    riskLevel: "높음",
    owner: "김대리",
    next: "초안 보기",
    tone: "orange",
    detail: {
      title: "Nguyen V. 체류기간 연장 서류 요청",
      statusBadges: ["D-30", "우선 확인", "승인 전"],
      subject: "Nguyen Van A",
      nationality: "베트남",
      visaType: "E-9",
      channel: "Zalo",
      language: "베트남어",
      visaExpiryDate: "2026.06.20",
      contractEndDate: "2026.07.01",
      why:
        "체류기간 만료까지 30일 남았고, 표준근로계약서 사본과 여권 사본이 아직 확인되지 않았습니다. 승인 없이 외부 발송은 진행되지 않습니다.",
      prepared: [
        "베트남어 서류 요청 메시지 초안 생성",
        "한국어 번역본 생성",
        "행정사 검토용 자료 패키지 준비",
        "이전 대화 기록 확인",
        "예상 응답 시나리오 생성",
      ],
      missingDocuments: ["표준근로계약서 사본", "여권 사본"],
      nextActions: [
        "Nguyen에게 서류 요청 메시지 발송 승인",
        "응답 없을 경우 2일 뒤 리마인드 제안",
        "서류 수신 후 행정사 검토 자료 생성",
      ],
      evidence: [
        "체류만료일: 2026.06.20",
        "최근 서류 상태: 표준근로계약서 사본 누락, 여권 사본 누락",
        "이전 메시지: 3일 전 서류 요청 기록 있음",
        "승인 전 외부 발송 제한 적용",
      ],
      judgmentRecordId: "4789",
    },
  },
  {
    kind: "hiring",
    title: "신규 베트남 E-9 3명 채용 요청",
    target: "송출회사 요청서",
    worksiteLine: "화성 1공장 조립라인",
    status: "준비 중",
    deadline: "이번 주",
    riskLevel: "중간",
    owner: "박대리",
    next: "요청서 보기",
    tone: "blue",
    detail: {
      title: "신규 베트남 E-9 3명 채용 요청",
      statusBadges: ["준비 72%", "쿼터 검토", "행정사 확인 필요"],
      subject: "송출회사 요청서",
      why:
        "추가 고용 가능성을 검토할 수 있는 상태지만, 최종 가능 여부는 고용센터와 행정사 확인이 필요합니다. 후보자 점수화나 국적별 우열 판단은 하지 않습니다.",
      prepared: [
        "고용 쿼터 확인",
        "채용 의도 분석",
        "신청 서류 초안 작성",
        "내국인 구인노력 기간 산정",
        "채용 요청서 초안 생성",
      ],
      nextActions: ["요청서 검토", "준비 체크리스트 확인", "행정사 검토 요청"],
      evidence: [
        "요청 인원: 3명",
        "잔여 쿼터: 5명까지 추가 고용 가능성 검토",
        "준비 상태: 72%",
        "최종 판단: 고용센터 / 행정사 확인 필요",
      ],
      judgmentRecordId: "4790",
    },
  },
  {
    kind: "doc",
    title: "Candidate A 입국 전 서류 패키지",
    target: "Candidate A",
    worksiteLine: "도장라인",
    status: "승인 대기",
    deadline: "5/20",
    riskLevel: "중간",
    owner: "김대리",
    next: "승인 요청",
    tone: "orange",
    detail: {
      title: "Candidate A 입국 전 서류 패키지",
      statusBadges: ["승인 대기", "5/20 마감", "검토 필요"],
      subject: "Candidate A",
      why: "입국 전 제출 서류 패키지가 일부 준비됐지만, 행정사 검토 전 담당자 승인이 필요합니다.",
      prepared: ["건강진단서 원본 확인", "입국 전 교육 수료증 확인", "근로계약서 사본 확인"],
      missingDocuments: ["건강진단서 원본", "입국 전 교육 수료증"],
      nextActions: ["대표 승인 요청", "행정사 검토 자료 확정", "후보자 안내 메시지 준비"],
      evidence: ["승인 마감: 2026.05.20", "준비 완료도: 45%", "행정사 검토 전 확인 필요"],
      judgmentRecordId: "4786",
    },
  },
  {
    kind: "message",
    title: "계약 종료 확인",
    target: "Tran T. H.",
    worksiteLine: "포장라인",
    status: "응답 도착",
    deadline: "5/12",
    riskLevel: "낮음",
    owner: "김대리",
    next: "응답 요약",
    tone: "green",
    detail: {
      title: "Tran T.H. 계약 종료 응답 확인",
      statusBadges: ["응답 도착", "요약 확인", "다음 절차 확인"],
      subject: "Tran T. H.",
      nationality: "베트남",
      visaType: "E-9",
      channel: "Zalo",
      language: "베트남어",
      why: "근로자 응답이 도착했으며, 계약 종료 관련 내용을 담당자가 확인해야 합니다.",
      prepared: ["외국어 응답 요약", "한국어 업무 메모 생성", "다음 절차 확인 항목 정리"],
      nextActions: ["응답 요약 확인", "계약 종료 일정 재확인", "필요 시 추가 질문 전송"],
      evidence: ["응답 도착: 2026.05.11", "계약 종료일: 2026.06.22", "체류만료일: 2026.09.15"],
      judgmentRecordId: "4788",
    },
  },
];

export const contactItems = [
  { initials: "N", worker: "Nguyen V.", country: "VN", badge: "2", desc: "표준근로계약서 사본과 여권 사본을 ...", status: "초안", date: "2026-05-11" },
  { initials: "T", worker: "Tran T. H.", country: "VN", badge: "2", desc: "계약 종료 관련 확인 요청에 응답이 ...", status: "응답 도착", date: "2026-05-11" },
  { initials: "M", worker: "Mohammad I.", country: "BD", badge: "S", desc: "재계약 근로계약서 수령 안내 초안이...", status: "승인 대기", date: "2026-05-10" },
];

export const judgmentRows = [
  { id: "#4789", worker: "Nguyen V.", status: "승인 완료", tone: "green" as Tone, date: "2026-05-21" },
  { id: "#4790", worker: "Nguyen V.", status: "발송 예정", tone: "blue" as Tone, date: "2026-05-21" },
  { id: "#4788", worker: "Tran T. H.", status: "수정 요청", tone: "orange" as Tone, date: "2026-05-20" },
  { id: "#4787", worker: "김민수", status: "담당자 확인", tone: "green" as Tone, date: "2026-05-20" },
  { id: "#4786", worker: "Candidate A", status: "승인 대기", tone: "orange" as Tone, date: "2026-05-19" },
  { id: "#4785", worker: "Nguyen V.", status: "발송 예정", tone: "blue" as Tone, date: "2026-05-19" },
  { id: "#4784", worker: "Pham T. A.", status: "승인 완료", tone: "green" as Tone, date: "2026-05-18" },
  { id: "#4783", worker: "Candidate B", status: "승인 대기", tone: "orange" as Tone, date: "2026-05-18" },
  { id: "#4782", worker: "Nguyen V.", status: "담당자 확인", tone: "green" as Tone, date: "2026-05-17" },
  { id: "#4781", worker: "Bayar M.", status: "검토 자료 준비", tone: "blue" as Tone, date: "2026-05-17" },
];

export const adminPackage = {
  title: "Bayar M. 케이스 검토 패키지",
  status: "승인 대기",
  createdAt: "2026-05-08 08:15",
  receiver: "고려행정사사무소",
  profile: [
    ["성명", "Bayar M. (마스킹: Bayar **)"],
    ["국적", "몽골"],
    ["체류자격", "E-9-1"],
    ["외국인등록번호", "880***-5*****"],
    ["사업장", "한별제조 / B동 도장공정"],
  ],
  stay: [
    ["체류만료일", "2026.05.05 (D+3, 만료 초과)"],
    ["계약종료일", "2026.05.05"],
    ["고용변동 신고기한", "2026.05.20 (D-12)"],
  ],
  docs: [
    ["여권 사본", "확보됨"],
    ["외국인등록증 사본", "확보됨"],
    ["근로계약서", "확보됨"],
    ["건강진단서", "만료"],
  ],
};
