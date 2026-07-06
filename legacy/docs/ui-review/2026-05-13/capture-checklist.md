# PC/Mobile UI Capture Checklist

## 기준

- 브랜치: `codex/pc-shell-dashboard-try`
- 앱: `http://127.0.0.1:3000`
- PC 기본 캡처: `1040x900`
- PC 상세 패널 검수 캡처: `1600x1000`
- 모바일 캡처: `430x932`
- 실제 외부 발송, 정부 제출, 행정사 자동 전달은 실행하지 않는다.

## 기준 이미지

### PC

- [ ] `targets/pc/01-dashboard-today.png` - 오늘 할 일
- [ ] `targets/pc/02-hiring.png` - 채용 준비
- [ ] `targets/pc/03-workers.png` - 근로자
- [ ] `targets/pc/04-contacts.png` - 컨택
- [ ] `targets/pc/05-visa.png` - 케이스
- [ ] `targets/pc/06-documents.png` - 행정사 검토
- [ ] `targets/pc/07-evidence.png` - 판단 기록

### Mobile

- [ ] `targets/mobile/01-agent-process.png` - AI 처리 과정
- [ ] `targets/mobile/02-draft.png` - 메시지 초안
- [ ] `targets/mobile/03-approval-done.png` - 승인 완료
- [ ] `targets/mobile/04-briefing.png` - 오늘 브리핑
- [ ] `targets/mobile/05-case-detail.png` - 서류 요청 상세

## 현재 화면 캡처

## 빠른 반복 검증

- 반복 수정 중에는 전체 화면 캡처를 매번 만들지 않는다.
- 먼저 아래 `data-testid` 기반 DOM 검증으로 클릭 대상을 고정한다.

| 목적 | selector |
| --- | --- |
| 상세 패널 | `dashboard-detail-panel` |
| 상세 패널 닫기 | `dashboard-detail-close` |
| 서류 보완 요약 카드 | `summary-docs` |
| Nguyen 행 | `worker-row-nguyen` |
| 초안 보기 | `action-draft` |
| 검토 자료 보기 | `action-handoff` |
| 승인 | `action-approval` |
| AI 반장 | `ai-fab` |
| 모바일 상세 진입 | `mobile-open-detail` |
| 모바일 브리핑 초안 | `mobile-briefing-draft` |
| 모바일 브리핑 승인 | `mobile-briefing-approve` |
| 모바일 처리 화면 초안 | `mobile-process-draft` |
| 모바일 초안 승인 | `mobile-draft-approve` |
| 모바일 상세 초안 | `mobile-detail-draft` |

- [x] 초기 상태: `dashboard-detail-panel = 1`
- [x] `dashboard-detail-close` 클릭 후: `dashboard-detail-panel = 0`
- [x] `summary-docs` 클릭 후: `dashboard-detail-panel = 1`
- [x] 다시 닫고 `worker-row-nguyen` 클릭 후: `dashboard-detail-panel = 1`
- [x] 모바일 브리핑: `mobile-briefing-approve`, `mobile-briefing-draft`, `mobile-open-detail` 각 1개
- [x] 모바일 승인 흐름: 브리핑 -> AI 처리 과정 -> 메시지 초안 -> 승인 완료
- [x] 모바일 상세 흐름: 브리핑 -> 서류 요청 상세 -> 초안 버튼 확인

## 최종 캡처

최종 캡처는 주요 UI 수정이 끝난 뒤 한 번만 갱신한다.

### PC 기본 라우트

- [ ] `/dashboard` -> `current/pc/01-dashboard-today.png`
- [ ] `/hiring` -> `current/pc/02-hiring.png`
- [ ] `/workers` -> `current/pc/03-workers.png`
- [ ] `/contacts` -> `current/pc/04-contacts.png`
- [ ] `/visa` -> `current/pc/05-visa.png`
- [ ] `/documents` -> `current/pc/06-documents.png`
- [ ] `/evidence` -> `current/pc/07-evidence.png`

### PC 상호작용 상태

- [ ] `/dashboard` 상세 패널 열린 상태 -> `current/pc/08-dashboard-detail-open.png`
- [ ] `/dashboard` 상세 패널 접힌 상태 -> `current/pc/09-dashboard-detail-collapsed.png`
- [ ] `/dashboard` 요약 카드 재클릭 후 펼침 -> `current/pc/10-dashboard-detail-reopened.png`
- [ ] 플로팅 `AI 반장` 클릭 -> `current/pc/11-ai-drawer.png`
- [ ] `초안 보기` 클릭 -> `current/pc/12-document-draft-preview.png`
- [ ] `검토 자료 보기` 또는 `요청서 보기` 클릭 -> `current/pc/13-handoff-preview.png`

### Mobile

- [ ] `/mobile/daily-briefing` 오늘 브리핑 -> `current/mobile/01-briefing.png`
- [ ] `보내기 승인` 클릭 후 AI 처리 과정 -> `current/mobile/02-agent-process.png`
- [ ] `초안 확인하기` 클릭 후 메시지 초안 -> `current/mobile/03-draft.png`
- [ ] `보내기 승인` 클릭 후 승인 완료 -> `current/mobile/04-approval-done.png`
- [ ] 브리핑에서 상세 진입 -> `current/mobile/05-case-detail.png`

## 검수 포인트

- [ ] 헤더 로고, 회사 칩, 검색창, 알림, 사용자 영역이 기준 이미지와 같은 위치에 있다.
- [ ] 탭 라벨은 `오늘 할 일 / 채용 준비 / 근로자 / 컨택 / 케이스 / 행정사 검토 / 판단 기록`이다.
- [ ] `/dashboard` 상세 패널은 PC 폭에서 오른쪽에 붙어 있고 아래로 떨어지지 않는다.
- [ ] 상세 패널 `X` 클릭 시 접히고, 요약 카드나 근로자 행 클릭 시 다시 펼쳐진다.
- [ ] 버튼 클릭은 drawer/modal/preview로 반응하고 실제 발송/제출/전달을 실행하지 않는다.
- [ ] 사용자 화면에 `Evidence`, `Handoff`, `Citation` 표현이 노출되지 않는다.
