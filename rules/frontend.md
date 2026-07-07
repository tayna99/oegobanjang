# rules/frontend — 프론트 컨벤션 (해당 작업 시 로드)

## 컴포넌트

- 함수형 + 명시적 Props 인터페이스. `export function ApprovalCard(props: ApprovalCardProps)`
- 파일 1개 = 컴포넌트 1개. 200줄 넘으면 분리 신호
- 공용(components/)은 도메인 타입 import 금지 — 프리미티브 props만
- 변형은 variant prop: `<Badge tone="pending">`. 새 tone이 필요하면 tokens와 1단계 §0.2 표에 먼저 추가
- 조건부 클래스는 `cn()` 유틸 (기존 코드 승계)

## 상태

- 서버성 상태(케이스·승인·기록)는 zustand 스토어, UI 로컬 상태(시트 열림 등)는 useState
- 스토어 액션은 동사형: `caseStore.transition(caseId, to)`, `approvalStore.decide(id, 'approved', key)`
- 파생값은 selector로 — 컴포넌트에서 정렬·필터 로직 재구현 금지 (deterministic 정렬은 selector 한 곳)

## 라우팅

- 딥링크 파라미터는 zod로 파싱·검증, 대상 없으면 `/` + 토스트 "이미 처리된 업무입니다"
- 화면 이동 헬퍼 `nav.toCase(id)` 사용 — 문자열 경로 하드코딩 금지

## 테스트

- 각 화면: 5상태 렌더 테스트 최소 1세트 (1단계 §0.1)
- 가드레일은 테스트가 스펙: GOTCHAS의 금지가 코드로 가능해지면 테스트가 먼저 실패해야 한다
- E2E는 해피패스 1개(승인 플로우)만 유지 — 무리한 E2E 증식 금지
- 시간 의존 테스트는 기준일 주입(`calcDday(date, base)`) — `new Date()` 직접 호출 금지(유틸 내부 제외)

## 접근성

- 터치 타깃 48px(승인 CTA 52px) — 히트 영역은 padding으로 확보
- 시트/모달에 role="dialog", 포커스 트랩
- 색만으로 정보 전달 금지 — 배지에 라벨 텍스트 병기
- `prefers-reduced-motion` 시 모든 모션 0ms + 스트리밍 일괄 표시
