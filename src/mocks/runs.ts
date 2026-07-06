// APPROVE 승인 런 설정 이식 — reference/prototype_v3.html의 APPROVE(§775)를
// 1단계 스펙 §M9 RunConfig/RunStep 계약으로 정규화 (M0.5, docs/SPEC_INDEX.md 이식표).
// 범위: mode='approval'(M4) 6건만 이식. command(#4790)·draft 재생성(#4796)·replay(#4788)는
// 각각 M1.5(런 엔진)·M3.1(프로액티브 런) 태스크에서 다룬다 — 여기서 앞서 설계하지 않는다.

export type RunStepKind = 'thinking' | 'tool_call' | 'guardrail' | 'wait';
// 공식 RunStep(GLOSSARY §16)은 thinking/tool_call/guardrail/handoff/replan 5종.
// 'wait'는 이 6건의 승인 대기 스텝을 표현하려 v3 데모를 따라 추가한 로컬 확장이며,
// M9 RunStep으로 승격할 때는 스펙에 먼저 추가해야 한다(GOTCHAS 상단 원칙).

export interface RunStep {
  kind: RunStepKind;
  label: string; // v3 l — 스텝 제목
  detail: string; // v3 d — 설명/결과 요약
}

export interface RunConfig {
  runKey: string; // APPROVE 레지스트리 키 — DRAFT.draftKey와 연결
  caseId?: string; // 대응하는 CaseCard.caseId (candidate는 패키지 전용이라 없음)
  mode: 'approval'; // M4 화면(승인 직전) 전용. dock은 항상 'approve'로 고정
  title: string;
  agent: string; // 라우팅된 에이전트명
  evidenceRef: string; // "#4789" 판단 기록 번호
  autonomyLabel: string; // "자율성 Medium (승인 필요)" 등 meta 문구
  question: string; // 승인 질문(q)
  altLabel: string; // 대안 버튼 라벨(수정 요청/돌아가기 등)
  steps: RunStep[];
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
      { kind: 'wait', label: '발송 전 승인 대기', detail: '담당자 승인 후 근로자에게 발송됩니다' },
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
      { kind: 'wait', label: '전달 준비 승인 대기', detail: '승인 후 행정사 전달 준비 완료로 전환됩니다' },
    ],
  },
  {
    runKey: 'bayarPkg',
    caseId: 'bayar',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Visa Document Agent',
    evidenceRef: '#4793',
    autonomyLabel: 'high risk — 행정사 전달 강제',
    question: '검토 자료를 행정사에게 전달할 준비로 승인할까요?',
    altLabel: '돌아가기',
    steps: [
      { kind: 'tool_call', label: '케이스 상태 정리', detail: '체류만료 D+3 · CRITICAL' },
      { kind: 'tool_call', label: '관련 규정 수집', detail: '출입국관리법 제25조·제94조 (근거 A)' },
      { kind: 'tool_call', label: '검토 자료 초안 생성', detail: '서류 3종 + 쟁점 요약 포함' },
      { kind: 'guardrail', label: '가드레일 · high risk', detail: '기한 경과 케이스 — 앱 처리 불가, 행정사 검토로만 진행됩니다' },
    ],
  },
  {
    runKey: 'mohammad',
    caseId: 'mohammad',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Multilingual Contact Agent',
    evidenceRef: '#4794',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '이 요청을 발송 승인할까요?',
    altLabel: '수정 요청',
    steps: [
      { kind: 'tool_call', label: '서류 만료 확인', detail: '건강검진 확인서 · 7.18 만료 예정' },
      { kind: 'tool_call', label: '요청 초안 생성 완료', detail: '한국어 + 영어' },
      { kind: 'wait', label: '발송 전 승인 대기', detail: '담당자 승인 후 발송됩니다' },
    ],
  },
  {
    runKey: 'hiring',
    caseId: 'hiring',
    mode: 'approval',
    title: '승인 전 확인',
    agent: 'Workforce Agent',
    evidenceRef: '#4795',
    autonomyLabel: '자율성 Medium (승인 필요)',
    question: '요청서를 행정사 검토로 보낼까요?',
    altLabel: '돌아가기',
    steps: [
      { kind: 'tool_call', label: '요청서 완성도 점검', detail: '8개 항목 중 5개 완료' },
      { kind: 'thinking', label: '미완료 항목 판단', detail: '남은 3개는 행정사 확인과 병행 가능' },
      { kind: 'guardrail', label: '가드레일', detail: '후보자 평가·국적 선호 항목 없음 확인 — 준비 상태 점검만 포함' },
      { kind: 'wait', label: '검토 요청 승인 대기', detail: '승인 후 행정사에게 검토 요청됩니다' },
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
      { kind: 'wait', label: '발송 전 승인 대기', detail: '담당자 승인 후 발송됩니다' },
    ],
  },
];
