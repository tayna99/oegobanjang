import { formatClockTime } from '@/lib/threads';
import { useSessionStore } from '@/stores/sessionStore';
import type { Channel, Message, MessageDirection, MessageThread, WorkerRef } from '@/types';
import { apiFetch } from './client';

// GET /api/v1/threads · GET /api/v1/threads/{id} 응답 DTO
// (백엔드 backend/app/schemas/thread.py, snake_case). R2.3, NEXT_ROADMAP 2.3.
export interface ThreadWorkerDto {
  display_name: string;
  nationality: string;
  team: string | null;
}

export interface InterpretationDto {
  id: string;
  summary_ko: string;
  confidence: string;
  status: string;
  confirmed_at: string | null;
}

export interface MessageDto {
  id: string;
  direction: string;
  channel: string;
  lang: string | null;
  body_original: string | null;
  body_ko: string | null;
  received_at: string | null;
  created_at: string;
  interpretation: InterpretationDto | null;
}

export interface ThreadDto {
  id: string;
  worker: ThreadWorkerDto | null;
  channel: string;
  last_message_at: string | null;
  message_count: number;
  latest_interpretation_status: string | null;
}

export interface ThreadDetailDto {
  id: string;
  worker: ThreadWorkerDto | null;
  channel: string;
  messages: MessageDto[];
}

const CHANNEL_LABELS: Record<Channel, string> = { sms: 'SMS', alimtalk: '알림톡', zalo: 'Zalo', email: '이메일' };

// threads.channel은 DB에 CHECK 제약이 없는 자유 텍스트다(db/schema.sql:488) — 시드 데이터는
// 프론트 Channel 값과 항상 일치하지만, 알려지지 않은 값이 오면 원문 그대로 표기해 숨기지 않는다.
function toChannel(raw: string): { channel: Channel; label: string } {
  const channel = raw as Channel;
  return { channel, label: CHANNEL_LABELS[channel] ?? raw };
}

// threads.worker_id는 NOT NULL(db/schema.sql:487)이라 실제로는 항상 존재한다 — worker가 조회
// 안 되는 경우(서비스 계층의 방어적 None)만을 위한 자리표시자.
function toWorkerRef(dto: ThreadWorkerDto | null): WorkerRef {
  if (!dto) return { displayName: '알 수 없음', nationality: '-', maskLevel: 'masked' };
  return { displayName: dto.display_name, nationality: dto.nationality, team: dto.team ?? undefined, maskLevel: 'masked' };
}

// thread_messages.direction ∈ {'inbound','system'}(db/schema.sql:508) — 'outbound'가 아니다.
// inbound(근로자→회사)는 프론트의 'in', system(회사 자동 응답)은 'out'에 대응한다.
function toDirection(raw: string): MessageDirection {
  return raw === 'inbound' ? 'in' : 'out';
}

function toMessage(threadId: string, dto: MessageDto): Message {
  return {
    messageId: dto.id,
    threadId,
    direction: toDirection(dto.direction),
    channel: toChannel(dto.channel).channel,
    body: dto.body_ko ?? dto.body_original ?? '',
    lang: dto.lang ?? 'ko',
    at: dto.created_at,
  };
}

// interpretations.status ∈ {'proposed','confirmed','discarded'}(db/schema.sql:527) —
// MessageThread.interpretationStatus 어휘로 사상. 'discarded'는 더 이상 유효하지 않은 해석이라
// 'none'과 동일하게 취급한다.
function toInterpretationStatus(status: string | undefined): MessageThread['interpretationStatus'] {
  if (status === 'proposed') return 'pending_review';
  if (status === 'confirmed') return 'confirmed';
  return 'none';
}

// R2.3 스코프 축소 — 여기서 채우지 않는 것:
// - thread.interpretation(대화형 확인 카드): 백엔드 InterpretationOut은 summary_ko·confidence·
//   status만 내려주고, 카드가 필요로 하는 updates/recommendedActions/caseId는 아직 없다.
//   해석 확인(confirmInterpretation)은 승인 결정과 같은 성격의 쓰기 동작이라 2.4류 다음
//   세션으로 미뤘다(로컬 스토어 뮤테이션 경로는 그대로 유지) — 값을 지어내지 않는다.
// - thread.caseId/draftCaseId: threads 테이블엔 case_id 컬럼 자체가 없다(drafts를 거쳐야
//   연결되는데 2.3 스코프 밖).
// - thread.preview: 목록에 원문 노출 금지 정책(ThreadListItem.tsx 주석)이라 메시지 내용을
//   쓰지 않고, 상태 파생 요약 문장만 쓴다.
function summarizePreview(status: MessageThread['interpretationStatus'], messageCount: number): string {
  if (status === 'pending_review') return '응답이 도착했습니다';
  if (status === 'confirmed') return '확인 완료';
  if (messageCount === 0) return '아직 응답이 없습니다';
  return `메시지 ${messageCount}건`;
}

export function toThreadSummary(dto: ThreadDto): MessageThread {
  const { channel, label } = toChannel(dto.channel);
  const interpretationStatus = toInterpretationStatus(dto.latest_interpretation_status ?? undefined);
  return {
    threadId: dto.id,
    workerRef: toWorkerRef(dto.worker),
    channel,
    channelLabel: label,
    messages: [],
    interpretationStatus,
    preview: summarizePreview(interpretationStatus, dto.message_count),
    timeLabel: dto.last_message_at ? formatClockTime(dto.last_message_at) : '',
  };
}

export function toThreadDetail(dto: ThreadDetailDto): MessageThread {
  const { channel, label } = toChannel(dto.channel);
  const messages = dto.messages.map((m) => toMessage(dto.id, m));
  const latestStatus = [...dto.messages].reverse().find((m) => m.interpretation)?.interpretation?.status;
  const interpretationStatus = toInterpretationStatus(latestStatus);
  const last = dto.messages[dto.messages.length - 1];
  return {
    threadId: dto.id,
    workerRef: toWorkerRef(dto.worker),
    channel,
    channelLabel: label,
    messages,
    interpretationStatus,
    preview: summarizePreview(interpretationStatus, dto.messages.length),
    timeLabel: last ? formatClockTime(last.created_at) : '',
  };
}

// 목록(가벼운 요약) — 배지·정렬에 필요한 해석 상태는 latest_interpretation_status로 이미
// 정확하다. 메시지 본문·전체 대화는 열람 시 fetchThreadDetail로 채운다.
export async function fetchThreads(): Promise<MessageThread[]> {
  const token = useSessionStore.getState().token ?? undefined;
  const dtos = await apiFetch<ThreadDto[]>('/api/v1/threads', { token });
  return dtos.map(toThreadSummary);
}

export async function fetchThreadDetail(threadId: string): Promise<MessageThread> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<ThreadDetailDto>(`/api/v1/threads/${threadId}`, { token });
  return toThreadDetail(dto);
}
