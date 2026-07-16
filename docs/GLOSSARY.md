# GLOSSARY — 도메인 용어집 (코드 네이밍 사전)

> 코드의 식별자는 이 표의 영문을 쓴다. 같은 개념에 두 이름 금지.

| 한국어 | 코드 | 정의 |
|---|---|---|
| 케이스 | `Case` | 업무(요청) 단위 작업 항목. 근로자 단위 아님 (결정 D2) |
| 오늘 브리핑 | `Briefing` | 매일 생성되는 승인/확인 필요 카드 묶음 (M1) |
| 다음 행동 | `NextAction` | 케이스에 붙는 실행 후보. state: locked/ready/scheduled/waiting |
| 승인 | `Approval` | 사람의 결정. pending/approved/rejected. 외부 발송의 유일한 관문 |
| 판단 기록 | `EvidenceEvent` | append-only 감사 이벤트. `#4789` 형식 ref |
| 위험도 | `Severity` | CRITICAL/HIGH/MEDIUM/LOW — Rule Engine 산출, LLM 판단 아님 |
| D-day | `dDay` | 기준일 대비 잔여일. 음수=경과(D+N 표기) |
| 에이전트 런 | `Run` | 툴콜링 루프 1회 실행. startedBy: user/event |
| 프로액티브 런 | proactive run | 이벤트(D-30 진입 등)가 자동 시작한 런. 산출물=준비된 카드 |
| 런 스텝 | `RunStep` | thinking/tool_call/guardrail/handoff/replan |
| 가드레일 | guardrail | 도구 레벨 차단. UI에 숨기지 않고 스텝으로 노출 |
| 핸드오프 | `handoff` | (1) 서브에이전트 간 위임 스텝 (2) 행정사 전달 패키지 — 문맥 구분 |
| 행정사 패키지 | `HandoffPackage` | 전문가 검토용 자료 묶음. 전달 준비까지만, 제출 없음 |
| 응답 해석 | `Interpretation` | 근로자 응답의 요약+상태 업데이트 제안. `isFinal:false` 필수 |
| 자율성 | `autonomy` | low/medium/high. MVP는 medium 고정(승인 필요) |
| 근거 | `Citation` | 법령·공식 안내. grade: A(법령)/B(공식)/C(통계)/E(내부) |
| 서류 준비율 | `readinessPercent` | 필수 서류 확보 비율. 사람 평가 지표 아님 |
| 체류만료 | `visaExpiresAt` | E-9 체류 만료일 |
| 계약종료 | `contractEndsAt` | 근로계약 종료일. 체류만료와 충돌 감지 대상 |
| 충돌 감지 | `contractVisaConflict` | 계약종료 < 체류만료 등 정합성 룰 |
| 누락 서류 | `missingDocument` | 필수 서류 미확보 상태 |
| 마스킹 | `maskId()` | PII 표시용 유틸. `***-*******` |
| 승인 대기 | `approval_pending` | 케이스가 사람 결정을 기다리는 상태 |
| 발송 승인 완료 | — | "발송 완료"라고 쓰지 않는다. MVP는 발송하지 않음 |
| 리마인드 | `reminder` | 미응답 시 재요청 **제안**. 자동 발송 아님 — scheduled 액션 |
| 테넌트 | `companyId` | 회사 격리 범위. 모든 조회의 첫 필터 |
| 역할 | `Role` | owner(대표)/manager(담당자)/viewer/expert(행정사, 링크 수신자) |
| 채널 | `Channel` | 근로자 발신·수신 경로. `'sms' \| 'alimtalk' \| 'zalo' \| 'email'` — email은 근로자 채널이 아니라 행정사 패키지 전달 전용 (`docs/MESSAGING_CHANNELS.md` §1) |
| 발송 대기열 | `Outbox` | 승인(human_approved) 이후 채널로 나가기 직전의 단일 지점. 발송 창·idempotency·리마인드 쿨다운을 여기서 한 번만 강제 (`docs/MESSAGING_CHANNELS.md` §2) |
| 응답 링크 | response link | 발신 메시지에 심는 만료형 토큰 링크로 근로자 응답을 받는 인바운드 패턴. SMS에 수신 API가 없고 Zalo OA 심사 전에도 채널 무관하게 동작하기 위한 1차 실연동 방식 (`docs/MESSAGING_CHANNELS.md` §3) |

## 인물 fixture (프로토타입 v3 승계)

| 이름 | 역할 | 시나리오 |
|---|---|---|
| Nguyen V. | 베트남 · E-9 · Zalo | D-30 체류연장, 누락 2건 — 승인 해피패스 주인공 |
| Tran T.H. | 베트남 · Zalo | 계약-체류 충돌 + 응답 도착 → 해석(M6) |
| Bayar M. | 몽골 · SMS | D+3 경과 — high risk 행정사 핸드오프 |
| Mohammad I. | 방글라데시 · SMS | 건강검진 만료 예정 — 서류 보완 |
| Candidate A | 베트남 후보자 | 입국 전 패키지 — 행정사 검토 |
