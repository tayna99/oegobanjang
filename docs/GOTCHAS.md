# GOTCHAS — 함정과 절대 금지 (에이전트 필독)

> 이 파일의 규칙은 협상 불가. 위반 코드는 verifier 서브에이전트가 반려한다.

## 1. 도메인 가드레일 (제품의 생존선)

| 금지 | 이유 | 올바른 패턴 |
|---|---|---|
| `sendMessage()` 같은 직접 발송 함수 | 승인 전 발송 구조적 차단 | 액션의 종착점은 항상 `requestApproval(action)` → 승인 후에도 MVP는 mock dispatch 경계까지만 |
| 비자 가능/불가능 판정 로직·문구 | 법률 판단 금지 | "검토가 필요합니다" + 행정사 핸드오프 |
| 후보자 점수화, 성실도/이탈 필드 | 사람 평가 금지 | 요건 충족 여부(boolean)와 준비도(%)만 |
| 국적 기반 정렬·필터·색상 강조 | 차별 금지 | 국적은 무채색 텍스트 정보로만 |
| 외국인등록번호/여권번호 원문 | PII | `maskId()` — fixture에도 원문 넣지 말 것 |
| EvidenceEvent 수정·삭제 | 감사 무결성 | append-only. 정정도 새 이벤트로 |
| high risk 케이스(기한 경과, 계약 종료 등)의 앱 내 처리 액션 | 전문가 영역 | `handoff` 액션으로만 — UI에 처리 버튼을 만들지 않는다 |
| 승인 버튼의 즉시 활성화 (런 스트리밍 중) | 성급한 승인 방지 | 스텝 렌더 완료 후 enable |
| 오프라인 상태에서 승인 API 호출 | 승인은 서버 확정 필수 | 버튼 disabled + 토스트 |
| PIN(`lib/pin.ts` DEMO_PIN)을 실제 인증으로 취급 | 데모용 고정값 목업, 실제 인증 백엔드 없음 | 승인 결정(approve/reject)은 `useApprovalActions` 공유 유닛(`lib/approval.ts`) 한 곳만 거친다 — 새 화면에 별도 승인 실행 경로를 만들지 않는다 |
| owner 역할의 쓰기-도구 커맨드 런 진입 | owner는 승인만, 실행 대리 아님(7단계 §2 각주3) | `RunConfig.writesData`가 true인 커맨드 런은 owner 차단. approval-mode 런은 게이트 대상 아님 |

## 2. 상태 전이 (이 순서 밖의 전이는 버그)

```
Case.state:      draft → risk_review → approval_pending → human_approved → completed
                                       ⇅ returned (반려 — 사유는 판단 기록에 남고, 보완 후 approval_pending 재진입만 허용. 왕복 밖 전이는 가드레일이 거부)
                                     ↘ blocked (근거 없음·high risk·오류 — 조용히 넘어가지 말고 표면화)
NextAction.state: locked → ready → scheduled|waiting
Approval.status:  pending → approved | rejected  (idempotency key 필수 — 중복 승인 차단)
```

- citation 0건이면 승인 버튼은 `locked`로 강등 (근거 품질 게이트)
- 승인 성공 응답 전에 로컬 상태를 approved로 바꾸지 않는다 (optimistic update 금지 — 승인만은 예외적으로 서버 확정 후 반영)

## 3. UI/카피 함정

- 고정 문구는 글자 하나도 바꾸지 않는다: **"승인 전에는 외부 발송이 차단됩니다."**
- 에러 문구에 "문제가 발생했습니다"류 금지 — 원인 1줄 + 행동 1개
- 스켈레톤에 수치 렌더 금지 — D-day·건수는 `--`
- 필(9999px) radius, 그라데이션, 컬러 아이콘 타일, 마스코트, 이모지 금지
- primary 파랑(#0066FF)은 **단일 초점 화면**에서 CTA 1개 + 활성 탭 + 포커스 링만. **예외**: 승인 큐처럼 동일 액션("검토")이 카드마다 반복되는 리스트는 카드별 파랑 CTA 허용(디자인 §2a 채택, 2026-07-11) — 위계가 아니라 반복 액션이므로
- **브리핑 카드 CTA는 "검토" 1개** (M2.6 개정, Mobile.dc.html §2a — 구 "정확히 2개" 규칙 대체). 카드에서 승인 불가 — 승인 진입은 검토 깔때기(2b 사례 검토 → 2c 체크리스트)로만. 승인 게이트 = 필수 체크리스트 N/N + citation-0 잠금(이중)
- 근로자 원문 메시지를 목록 미리보기에 노출 금지 (스레드 내부에서만)
- **승인은 케이스(액션) 단위로만 — 일괄 승인 UI·API 금지** (PC §3a 각주 비준, 2026-07-11. approvalStore에 batch 계열 메서드를 만들지 않는다)
- **F등급(합성 데이터) 근거 사용 불가** — citation-0 잠금 판정은 `usableCitations()`를 거친다(§3c 각주 비준)

## 4. 코드 함정

- 같은 목적의 컴포넌트를 두 번 만들지 않는다 — 만들기 전에 `src/components/` 검색. Chip/Card/Button 변형은 variant prop으로
- 케이스 시트(M2)는 하나다 — 케이스 종류별로 시트 컴포넌트를 복제하지 말고 데이터로 구동 (프로토타입 v3의 CASE 레지스트리 패턴)
- 런 화면(M4/M9/재생)도 하나다 — `renderRun(config)` 패턴 유지 (mode: approval|command|replay)
- D-day는 문자열이 아니라 날짜 계산 — `calcDday(date, base)` 유틸 하나만, 배지 색은 여기서 파생
- 시간·정렬은 deterministic: severity → dDay → 유형 우선순위 → id. 랜덤·현재시각 의존 정렬 금지 (테스트 불가능해짐)
- Tailwind 임의값(`text-[#354153]`) 금지 — tokens.css 변수를 theme에 등록해 사용
