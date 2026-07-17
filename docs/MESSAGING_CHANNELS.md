# MESSAGING_CHANNELS — 메시징 채널 아키텍처

> 목적: "발신"과 "수신"을 하나의 파이프라인으로 섞지 않는다. 발신은 승인 게이트 뒤에 있는 대기열이고, 수신은 근로자 응답을 정규화하는 별도 경로다. 이 문서는 MVP(프론트 mock 경계)와 백엔드 실연동 사이의 계약을 고정한다.

## 1. 원칙

**발신과 수신은 다른 문제다.** 같은 `MessageThread` 안에 쌓이지만 파이프라인은 별개로 설계한다 — 발신은 `Approval → Outbox → ChannelAdapter`(§2), 수신은 `인바운드 → 정규화 → Interpretation`(§3)이며 둘은 서로를 호출하지 않는다.

**근로자 채널 = SMS / 알림톡 / Zalo.** `src/mocks/threads.ts`의 인물 fixture가 이미 채널을 배정하고 있다(6인 로스터는 `docs/GLOSSARY.md` §인물 fixture 참조) — Nguyen Van A·Tran Thi H.는 Zalo, Batbayar E.는 SMS. 이메일은 근로자 채널에 없다.

**이메일은 행정사 패키지 전달 전용.** 통합설계_v1.md §2.6: "행정사는 앱 사용자가 아니라 **수신자**: 승인된 패키지를 링크/PDF로 받는다 (Handoff Preview)." 근로자에게 이메일 채널을 열지 않는다 — 행정사 패키지 어댑터는 §2의 근로자 채널 어댑터 4종과 분리한다.

**승인 없는 발신 없음.** 통합설계_v1.md §4.3(Claude가 되물을 기준 항목)은 "승인 완료 후 실제 발송 시점" 질문에 대해 기존 문서 결론을 이렇게 못 박는다: "**발송은 MVP 범위 밖, 승인까지만**." 같은 문서 §5.1은 에이전트 런의 도구 가드레일을 이렇게 정의한다: "`send_message` 같은 외부 발송 도구는 존재하지 않거나, 호출 시 무조건 `pending_approval`을 반환 (승인 전 발송 구조적 차단 유지)." 이 저장소에 `sendMessage`류 발송 함수가 없는 이유가 이 두 절이다 — `docs/GOTCHAS.md` §1도 동일하게 금지한다.

**승인과 실행은 같은 순간이 아니다.** 7단계_권한모델_승인위임_v1.md §2 각주²: "승인과 실행의 분리: owner 승인 = 상태를 `human_approved`로 변경. 실제 발송 트리거는 manager의 실행 확인(1탭)으로 분리 — 기존 문서의 '실행은 PC에서' 흐름을 역할로 재정의. **발송 연동 전(MVP)에는 mock 경계까지만.**" 즉 `caseStore.transition(..., 'human_approved')`는 발신 파이프라인의 **입구**를 여는 이벤트일 뿐, 그 자체가 채널로 나가는 신호는 아니다 — Outbox가 그 사이에 있다(§2).

## 2. 발신 파이프라인

```
Approval(승인) ──▶ Outbox(발송 대기열) ──▶ ChannelAdapter.send()
   human_approved      재시도 · idempotency        MockAdapter (MVP)
   (§1 각주² 기준        · 발송 창 검사             SmsAdapter / AlimtalkAdapter
    manager 실행 확인)   · 쿨다운 · 재발송            ZaloAdapter / EmailAdapter
```

### Outbox의 역할

Outbox는 "채널로 나가기 직전" 단일 지점이다. 어댑터마다 같은 규칙을 각자 구현하지 않도록, 아래 검사를 어댑터 앞에서 한 번만 강제한다.

| 검사 | 규칙 | 근거 |
|---|---|---|
| 발송 창 | 21:00~익일 08:00 발송 보류 → 08:30 다이제스트 합류. CRITICAL(N03)만 22:00까지 허용 | 2단계_알림카탈로그_딥링크맵_v1.md §5.1 |
| 이벤트 idempotency | 같은 case + 같은 event_type + 같은 임계값은 1회만 | 2단계 §5.2 |
| 리마인드 쿨다운 | 같은 케이스의 재촉성 알림은 **24시간 내 재발송 금지** | 2단계 §5.2 |
| 승인 미응답 재발송 | 승인 요청 후 **48시간 미응답 → 1회 재발송**, 이후는 다이제스트에만 표시 | 2단계 §5.2 |

Outbox 아이템의 상태 전이는 `MessageDeliveryStatus`(§4)를 따른다. MVP는 `draft → pending_approval → sent`만 쓰고, 재시도·전달 실패 같은 백엔드 개념(`queued`/`delivered`/`failed`)은 Outbox가 실제 큐가 될 때 추가한다(§5 ②).

### ChannelAdapter 5종

| 어댑터 | 역할 | 연동 시점 |
|---|---|---|
| `MockAdapter` | 아무것도 실제로 보내지 않는다. `sent` 기록만 남기고 `externalId`는 발급하지 않는다 | 현 MVP (기본값) |
| `SmsAdapter` | SMS 발송(솔라피류) | 1차 실연동 후보(§5 ②) |
| `AlimtalkAdapter` | 카카오 알림톡 발송. 실패 시 SMS로 fallback | §5 ③ |
| `ZaloAdapter` | Zalo OA API 발송 | §5 ④ |
| `EmailAdapter` | 행정사 패키지 전달 전용. 근로자 채널이 아니다 | 패키지 화면(2.4)과 별도 태스크 |

### ChannelAdapter 인터페이스 (의사코드)

```ts
interface ChannelAdapter {
  channel: Channel;
  send(msg: Message): Promise<{ externalId?: string; deliveryStatus: MessageDeliveryStatus }>;
}
```

## 3. 수신 파이프라인

1차 실연동은 **"응답 링크" 패턴**이다.

```
발신 메시지(SMS/알림톡/Zalo)에 만료형 토큰 링크를 심는다
  → 근로자가 모국어 모바일 페이지에서 버튼 선택 + 자유입력으로 응답
  → 인바운드 정규화 (Message { direction: 'in' } 생성)
  → N02(worker_replied) 이벤트
  → M6 Interpretation (응답 해석)
```

이 패턴을 쓰는 이유는 두 가지다. SMS에는 수신 API가 없어 회신을 채널에서 직접 받을 방법이 없다. 그리고 Zalo OA의 승인(비즈니스 계정 심사) 전에도 전 채널에서 동일하게 동작한다 — 응답 링크는 채널이 아니라 자체 호스팅 페이지이므로 채널사 승인 상태와 무관하다.

Zalo OA webhook은 붙는 시점부터 **같은 정규화 지점**(`Message { direction: 'in' }` 생성)에 합류한다. 인바운드 소스가 응답 링크든 webhook이든 그 다음 단계(N02 → M6 Interpretation)는 동일하다.

N02 이벤트는 2단계_알림카탈로그_딥링크맵_v1.md에 이미 정의돼 있다 — §4.1 알림 카탈로그 표는 N02를 `worker_replied`(근로자 응답 수신, 수신자: 담당자)로 정의하고 딥링크를 `response/{threadId}`로 지정한다. §7 이벤트 소스 매핑 표는 N02를 "컨택 스레드 inbound 수신 → 응답 해석 에이전트 큐"로 연결하고 출처를 "M6 스펙, 화면구성 v2 §8"로 명시한다.

**근로자 응답 원문은 스레드 내부에서만 노출한다.** 목록 미리보기와 Evidence 요약에는 절대 포함하지 않는다 — `docs/GOTCHAS.md` §3: "근로자 원문 메시지를 목록 미리보기에 노출 금지 (스레드 내부에서만)". `MessageThread.preview`는 원문 대신 상태 요약 문자열이어야 하고, `evidenceStore.append()`가 남기는 `summary`도 마찬가지로 요약 문장만 담는다(원문 문장 포함 금지는 이 저장소의 절대 제약).

## 4. 도메인 모델

이 문서가 아래 타입들의 스펙 원본이다. 구현 시 `src/types.ts`에 그대로 옮기고, 필드를 바꿀 일이 있으면 여기부터 고친다.

```ts
export type Channel = 'sms' | 'alimtalk' | 'zalo' | 'email';

export type MessageDirection = 'out' | 'in';

// 백엔드 확장 예약: 'queued' | 'delivered' | 'failed' (Outbox가 실제 큐가 되는 §5 ②부터)
export type MessageDeliveryStatus = 'draft' | 'pending_approval' | 'sent';

export interface Message {
  messageId: string;
  threadId: string;
  direction: MessageDirection;
  channel: Channel;
  body: string;
  lang: string; // 근로자 모국어 코드 ('vi' | 'mn' | 'bn' ...) — 'ko'는 담당자 발신
  at: string; // ISO timestamp
  deliveryStatus?: MessageDeliveryStatus; // direction:'in'이면 없음
  evidenceRef?: string; // "#4789" — approval_decided 등 관련 판단 기록
  caseId?: string; // 스레드는 케이스와 1:1이 아니므로 메시지 단위로도 보관
  externalId?: string; // 어댑터가 반환한 채널사 메시지 ID. MockAdapter는 항상 undefined
}

// Interpretation.updates 원소 — 서류 상태 등 필드 단위 갱신 제안 1건
export interface InterpretationUpdate {
  field: string; // 갱신 대상 필드명("표준근로계약서" 등)
  from: string; // 갱신 전 상태 라벨
  to: string; // 갱신 후 상태 라벨
  badgeTone: string; // 배지/칩 톤 값(예: src/lib/chipTone.ts ChipTone) — Interpretation은 그 구현을 몰라야 하므로 string으로 느슨하게 연결
}

export interface Interpretation {
  interpretationId: string;
  threadId: string;
  caseId: string;
  summaryKo: string; // 근로자 응답의 한국어 요약 — 원문 문장을 포함하지 않는다
  confidence: 'high' | 'low'; // low면 "해석이 불확실합니다. 원문을 확인해주세요" 안내 필요 (1단계 M6)
  updates: InterpretationUpdate[];
  recommendedActions: { action: NextActionRef; reason: string }[]; // 기존 NextActionRef 재사용 — 문자열 라벨로 분기 금지(rules/frontend.md)
  isFinal: false; // 담당자 확인 전 확정 금지 (GLOSSARY.md: Interpretation "isFinal:false 필수")
  confirmedSummary?: string; // onConfirm 이후 확정된 요약. Evidence summary와 동일 문장이어야 함
  confirmedCardText?: string; // 확정 후 케이스 카드/브리핑에 노출할 축약 문구
  evidenceRef?: string;
}

export interface MessageThread {
  threadId: string;
  workerRef: WorkerRef; // src/types.ts WorkerRef 재사용 — 마스킹 원칙 동일 적용
  channel: Channel;
  channelLabel: string; // "Zalo" | "SMS" 등 표시용. 국적과 마찬가지로 색상 강조 금지
  caseId?: string; // 현재 연결된 케이스
  draftCaseId?: string; // 케이스 생성 전 임시 연결
  messages: Message[];
  interpretation?: Interpretation;
  interpretationStatus: 'none' | 'pending_review' | 'confirmed';
  preview: string; // 목록 미리보기 — 원문 대신 상태 요약만 (§3, GOTCHAS §3)
  timeLabel: string;
  reminderScheduledLabel?: string; // "리마인드 7.6 예정" 형식
}
```

**스레드=근로자 단위, 케이스=업무 단위**이며 1:1로 매핑하지 않는다. `docs/GLOSSARY.md`의 결정 D2("케이스는 업무(요청) 단위. 근로자 단위 아님")를 메시징 도메인에서도 그대로 지킨다 — 한 근로자(`MessageThread`)가 여러 케이스를 순차로 가로지를 수 있고, `Message.caseId`가 그 시점의 연결을 기록한다.

## 5. 단계 로드맵

| 단계 | 범위 | 비고 |
|---|---|---|
| ① 현 MVP | 프론트 `Message` 도메인 + mock 경계 | 이번 태스크(2.2). 어댑터는 `MockAdapter`만 |
| ② 백엔드 접속점 | outbox 테이블 + `SmsAdapter` + 응답 링크 인바운드 API | `MessageDeliveryStatus` 확장(`queued`/`delivered`/`failed`) 시점 |
| ③ 알림톡 확장 | `AlimtalkAdapter` + SMS fallback 체인 | 알림톡 실패 시에만 SMS 폴백 (2단계 §5.2 "채널 중복 금지"와 동일 원칙) |
| ④ Zalo 확장 | `ZaloAdapter`(OA webhook 인바운드 합류) | §3의 정규화 지점에 합류, 응답 링크와 공존 |
| 행정사 패키지 | `EmailAdapter` | 별도 태스크(2.4, 패키지 화면). 근로자 채널과 분리 유지 |

## 6. 기존 스펙 정합 표

| 스펙 출처 | 절 | 이 문서 섹션 |
|---|---|---|
| `reference/specs/통합설계_v1.md` | §4.3 (되물을 기준: "발송은 MVP 범위 밖, 승인까지만") | 1. 원칙 |
| `reference/specs/통합설계_v1.md` | §5.1 (`send_message` 도구 부재/`pending_approval` 강제) | 1. 원칙, 2. 발신 파이프라인 |
| `reference/specs/7단계_권한모델_승인위임_v1.md` | §2 각주² (승인=상태 전이, 실행=manager 확인 분리) | 1. 원칙, 2. 발신 파이프라인 |
| `reference/specs/2단계_알림카탈로그_딥링크맵_v1.md` | §5.1 (야간 발송 금지 21:00~08:00) | 2. 발신 파이프라인 |
| `reference/specs/2단계_알림카탈로그_딥링크맵_v1.md` | §5.2 (idempotency·리마인드 쿨다운·재발송) | 2. 발신 파이프라인 |
| `reference/specs/2단계_알림카탈로그_딥링크맵_v1.md` | §4.1(N02) · §7 (worker_replied 정의·이벤트 소스) | 3. 수신 파이프라인 |
| `docs/GOTCHAS.md` | §1 (발송 함수 금지), §3 (원문 미리보기 노출 금지) | 1. 원칙, 3. 수신 파이프라인 |
