// APPROVE 승인 런 설정 이식 — reference/prototype_v3.html의 APPROVE(§775)를
// 1단계 스펙 §M9 RunConfig/RunStep 계약으로 정규화 (M0.5, docs/SPEC_INDEX.md 이식표).
// 1.5(런 엔진)에서 command(#4790)·replay(#4788) 모드를 추가하고, 로컬 확장이었던
// 'wait' kind를 제거했다 — "승인 대기"는 RunStep이 아니라 런의 종착점(requestApproval(),
// ARCHITECTURE.md §5)이며 RunConfig.question/altLabel이 이미 그 정보를 담고 있다.
// (docs/superpowers/specs/2026-07-06-run-engine-steptimeline-design.md §2)

export type RunStepKind = 'thinking' | 'tool_call' | 'guardrail' | 'handoff' | 'replan';
// 공식 RunStep(GLOSSARY §16) 5종 — M9 RunStep과 완전히 동일한 값만 쓴다.

export interface RunStep {
  kind: RunStepKind;
  label: string; // v3 l — 스텝 제목
  detail: string; // v3 d — 설명/결과 요약
}

export interface RunConfig {
  runKey: string; // /run/:runId 조회 키 & DRAFT.draftKey 연결
  caseId?: string; // 대응하는 CaseCard.caseId (candidate는 패키지 전용이라 없음)
  mode: 'command' | 'approval' | 'replay'; // M9(command) | M4(approval) | #4788류(replay)
  title: string;
  agent: string; // 라우팅된 에이전트명
  evidenceRef: string; // "#4789" 판단 기록 번호
  autonomyLabel: string; // "자율성 Medium (승인 필요)" 등 meta 문구
  question: string; // 승인 질문(q)
  altLabel: string; // 대안 버튼 라벨(수정 요청/돌아가기 등)
  steps: RunStep[];
  readOnly?: boolean; // replay 전용 — 정적 재생, 승인/대안 버튼을 렌더하지 않는다
  resultCaseIds?: string[]; // command 전용(M9/3.2) — 런이 정리한 대상 케이스, 결과 카드에서 케이스로 연결
  writesData?: boolean; // 케이스/초안 등 쓰기 도구를 쓰는 command 런 — owner는 차단(4.2, 7단계 §2 각주3)
}

// approvalRun()의 고정 결과 문구 — 모든 승인 런 공통.
export const RUN_RESULT_NOTICE = '이 액션은 판단 기록에 저장됩니다.';

export const RUN_CONFIGS: RunConfig[] = [
  {
    runKey: 'nguyen',
    caseId: 'nguyen',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Multilingual Contact Agent',
    evidenceRef: '#4789',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '이 메시지로 컨택할까요?',
    altLabel: '수정 요청',
    steps: [
      { kind: 'tool_call', label: '근로자 프로필 확인 완료', detail: 'Nguyen Van A · 베트남 · E-9 · Zalo' },
      { kind: 'tool_call', label: '이전 대화 기록 확인 완료', detail: '3일 전 표준근로계약서 요청 이력 있음' },
      { kind: 'tool_call', label: '메시지 초안 생성 완료', detail: '베트남어 원문 + 한국어 번역' },
    ],
  },
  {
    runKey: 'candidate',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Workforce Agent',
    evidenceRef: '#4792',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '이 패키지를 행정사 전달 준비 상태로 승인할까요?',
    altLabel: '수정 요청',
    steps: [
      { kind: 'tool_call', label: '후보자 서류 상태 확인', detail: '5개 중 3개 확보 · 2개 확인 필요' },
      { kind: 'tool_call', label: '요건 충족 여부 점검', detail: '준비도 기준 — 사람 평가 항목 없음' },
      { kind: 'guardrail', label: '가드레일', detail: '정부 포털 제출 불가 — 행정사 전달 준비까지만 진행합니다' },
    ],
  },
  {
    runKey: 'batbayarPkg',
    caseId: 'batbayar',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Visa Document Agent',
    evidenceRef: '#4793',
    autonomyLabel: 'high risk — 행정사 전달 강제',
    question: '검토 자료를 행정사에게 전달할 준비로 승인할까요?',
    altLabel: '돌아가기',
    steps: [
      { kind: 'tool_call', label: '케이스 상태 정리', detail: '체류만료 D+2 · CRITICAL' },
      { kind: 'tool_call', label: '관련 규정 수집', detail: '출입국관리법 제25조·시행규칙 경과 시 조치 (근거 A)' },
      { kind: 'tool_call', label: '검토 자료 초안 생성', detail: '서류 3종 + 쟁점 요약 포함' },
      { kind: 'guardrail', label: '가드레일 · high risk', detail: '기한 경과 케이스 — 앱 처리 불가, 행정사 검토로만 진행됩니다' },
    ],
  },
  {
    runKey: 'siti',
    caseId: 'siti',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Workforce Agent',
    evidenceRef: '#4790',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '이 신고서 초안을 확인 완료로 승인할까요?',
    altLabel: '수정 요청',
    steps: [
      { kind: 'tool_call', label: '신고 기한 확인', detail: '고용변동 신고 · 7.13 기한 (D-3)' },
      { kind: 'tool_call', label: '신고서 초안 생성 완료', detail: '고용변동 신고서 · 근거 A·B 연결' },
    ],
  },
  {
    runKey: 'tranReminder',
    caseId: 'tranCase',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Multilingual Contact Agent',
    evidenceRef: '#4796',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '이 리마인드를 발송 승인할까요?',
    altLabel: '수정 요청',
    steps: [
      { kind: 'tool_call', label: '대화 맥락 확인', detail: '어제 여권 제출 약속 — 오늘 미수신' },
      { kind: 'tool_call', label: '리마인드 초안 생성', detail: '베트남어 + 한국어 · 부드러운 톤' },
    ],
  },
  {
    // 커맨드 데모 런 — 판단 기록 #4790이 디자인 §3c에서 Siti 승인 요청으로 확정되어
    // #4797로 재번호(2.5.4b, 블루프린트 §3 세계관 정합).
    runKey: '4797',
    mode: 'command',
    title: '이번 달 급한 직원 정리',
    agent: 'Workforce Agent',
    evidenceRef: '#4797',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '이번 달 급한 케이스 정리 결과를 승인할까요?',
    altLabel: '수정 요청',
    steps: [
      { kind: 'thinking', label: '이번 달 마감 케이스 판별', detail: 'D-day 30일 이내 · 승인 대기 상태 기준' },
      { kind: 'tool_call', label: '대상 케이스 3건 확인', detail: 'Nguyen(D-30) · Siti(신고 기한 D-3) · Batbayar(행정사 검토)' },
      { kind: 'tool_call', label: '케이스별 액션 초안 생성', detail: '메시지·신고서·검토 자료 3건' },
      // 3.4 데모 4막(8단계 §2 line 83) — 발송 도구는 승인 대기만 반환. 가드레일 작동을 숨기지 않고 스텝으로 노출.
      {
        kind: 'guardrail',
        label: '외부 발송 차단 · 승인 요청 전환',
        detail: '발송은 승인 전 차단되어 승인 요청으로 전환했습니다 — 자율은 루프에, 경계는 도구에',
      },
    ],
    // 3.2: 정리 결과 카드에서 곧바로 대상 케이스로 진입 — Batbayar는 기한 경과라 행정사 검토 게이트.
    resultCaseIds: ['nguyen', 'siti', 'batbayar'],
    // 4.2: 케이스별 액션 초안을 생성하는 쓰기 도구 — owner의 M9는 읽기성 요청만 허용(7단계 §2 각주3).
    writesData: true,
  },
  {
    // 케이스 타임라인 런 체이닝(3.3)의 1차 요청 기록 — CASE_SHEETS.nguyen.activity의
    // "#4712 · 1차 서류 요청 — 여권 사본 요청 — 승인·발송 완료"에 대응하는 재생 런
    // (코드리뷰 지적: 대응 config가 없어 클릭 시 무한 로딩이었다).
    runKey: '4712',
    caseId: 'nguyen',
    mode: 'replay',
    title: '1차 서류 요청 (재생)',
    agent: 'Multilingual Contact Agent',
    evidenceRef: '#4712',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '여권 사본을 요청할까요?',
    altLabel: '수정 요청',
    readOnly: true,
    steps: [
      { kind: 'tool_call', label: '근로자 프로필 확인 완료', detail: 'Nguyen Van A · 베트남 · E-9 · Zalo' },
      { kind: 'tool_call', label: '요청 메시지 초안 생성 완료', detail: '여권 사본 요청 · 베트남어 원문 + 한국어 번역' },
      {
        kind: 'guardrail',
        label: '발송 전 정지 · 승인 요청 생성',
        detail: '자율성 Medium — 근로자 컨택은 자동 발송하지 않고 담당자 승인 후 발송합니다',
      },
    ],
  },
  {
    runKey: '4788',
    caseId: 'nguyen',
    mode: 'replay',
    title: '서류요청 준비 (재생)',
    agent: 'Multilingual Contact Agent',
    evidenceRef: '#4788',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '이 메시지로 컨택할까요?',
    altLabel: '수정 요청',
    readOnly: true,
    steps: [
      { kind: 'tool_call', label: '근로자 프로필 확인 완료', detail: 'Nguyen Van A · 베트남 · E-9 · Zalo' },
      { kind: 'tool_call', label: '이전 대화 기록 확인 완료', detail: '3일 전 표준근로계약서 요청 이력 있음' },
      { kind: 'tool_call', label: '메시지 초안 생성 완료', detail: '베트남어 원문 + 한국어 번역' },
      // 3.1: 프로액티브 런은 발송 직전 가드레일에서 멈춘다 — 자율 발송 없이 담당자 승인 요청을 생성.
      // GOTCHAS "가드레일은 숨기지 않고 스텝으로 노출 — 신뢰 자산".
      {
        kind: 'guardrail',
        label: '발송 전 정지 · 승인 요청 생성',
        detail: '자율성 Medium — 근로자 컨택은 자동 발송하지 않고 담당자 승인 후 발송합니다',
      },
    ],
  },
];
