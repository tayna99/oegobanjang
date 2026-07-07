# PC/Mobile UI Diff Notes

## Summary

- 기준 이미지: `docs/ui-review/2026-05-13/targets`
- 현재 캡처: `docs/ui-review/2026-05-13/current`
- 최신 결정: `/dashboard`는 오른쪽 상세 패널을 포함한다.
- 검수 원칙: 차이를 먼저 기록하고, 작은 단위로 UI를 수정한다.

## PC

| 화면 | 기준 이미지 | 현재 캡처 | 상태 | 메모 |
| --- | --- | --- | --- | --- |
| 오늘 할 일 | `targets/pc/01-dashboard-today.png` | `current/pc/01-dashboard-today.png` | 대기 | 상세 패널 포함 상태도 별도 캡처 |
| 채용 준비 | `targets/pc/02-hiring.png` | `current/pc/02-hiring.png` | 대기 |  |
| 근로자 | `targets/pc/03-workers.png` | `current/pc/03-workers.png` | 대기 |  |
| 컨택 | `targets/pc/04-contacts.png` | `current/pc/04-contacts.png` | 대기 |  |
| 케이스 | `targets/pc/05-visa.png` | `current/pc/05-visa.png` | 대기 |  |
| 행정사 검토 | `targets/pc/06-documents.png` | `current/pc/06-documents.png` | 대기 |  |
| 판단 기록 | `targets/pc/07-evidence.png` | `current/pc/07-evidence.png` | 대기 |  |

## PC Interaction

| 상태 | 현재 캡처 | 상태 | 메모 |
| --- | --- | --- | --- |
| `/dashboard` 상세 패널 열림 | `current/pc/08-dashboard-detail-open.png` | 대기 | 오른쪽 컬럼 유지 확인 |
| `/dashboard` 상세 패널 접힘 | `current/pc/09-dashboard-detail-collapsed.png` | 대기 | X 클릭 후 확인 |
| `/dashboard` 상세 패널 재열림 | `current/pc/10-dashboard-detail-reopened.png` | 대기 | 요약 카드/행 클릭 후 확인 |
| AI drawer | `current/pc/11-ai-drawer.png` | 대기 | 플로팅 AI 반장 클릭 |
| 초안 preview | `current/pc/12-document-draft-preview.png` | 대기 | 실제 발송 없음 |
| 검토 자료 preview | `current/pc/13-handoff-preview.png` | 대기 | 실제 제출/전달 없음 |

## Mobile

| 화면 | 기준 이미지 | 현재 캡처 | 상태 | 메모 |
| --- | --- | --- | --- | --- |
| 오늘 브리핑 | `targets/mobile/04-briefing.png` | `current/mobile/01-briefing.png` | 대기 |  |
| AI 처리 과정 | `targets/mobile/01-agent-process.png` | `current/mobile/02-agent-process.png` | 대기 |  |
| 메시지 초안 | `targets/mobile/02-draft.png` | `current/mobile/03-draft.png` | 대기 |  |
| 승인 완료 | `targets/mobile/03-approval-done.png` | `current/mobile/04-approval-done.png` | 대기 | `업무 기록 #4789` 문구 확인 |
| 서류 요청 상세 | `targets/mobile/05-case-detail.png` | `current/mobile/05-case-detail.png` | 대기 |  |

## 발견 사항

- `data-testid` 기반으로 반복 검증 경로를 고정했다.
- `/dashboard` 상세 패널은 초기 1개, 닫기 후 0개, 요약 카드 클릭 후 1개, Nguyen 행 클릭 후 1개로 확인했다.
- 모바일은 브리핑 -> AI 처리 과정 -> 메시지 초안 -> 승인 완료 흐름과 브리핑 -> 서류 요청 상세 흐름을 확인했다.
- 전체 이미지 캡처는 주요 UI 수정 후 마지막에만 갱신한다.
