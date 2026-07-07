# rules/design — 디자인 토큰·UI 규칙 (UI 작업 시 로드)

> 전체 스펙: `reference/specs/4단계_모바일디자인토큰_v1.md`. 아래는 작업용 요약.
> 시각 기준: `reference/prototype_v3.html` — 여기 보이는 대로가 정답.

## 토큰 (tokens.css — v3 `:root` 그대로)

- 크롬: canvas #fff / surface #f2f3f8 / ink #354153(검정 금지) / muted #8b93a7 / faint #b4bbcb(placeholder 전용) / hairline #e5e8ef
- 브랜드: primary #0066FF — **화면당 CTA 1개 + 활성 탭 + 포커스 링 + 스파크 아이콘만**
- 기능색: critical #EF4444 / warning #F97316 / pending #B45309 / info #2563EB / success #00913A / neutral #6B7280 — 배지·도트·상태 텍스트 전용, 배경은 8~10% 틴트
- radius: input 12 / chip·badge 14 / card 16 / sheet 상단 20. 필·직각 금지
- 그림자: 카드 `0 4px 8px rgba(0,0,0,.10)` 단일. hero 카드만 그림자(보더 없음), 나머지 hairline 보더 — 동시 사용 금지
- 모션: fast 150 / standard 240(시트) / slow 360(M5 push-in 전용). ease-enter cubic-bezier(.2,0,0,1)

## 타이포

Pretendard, letter-spacing normal. 화면타이틀 20/700, 인사문장 23/700, 카드제목 16/600, 본문 15/400, 라벨 14/600, 캡션 12~13, 숫자 tabular-nums. weight 900 금지.

## 상태 표현

- 스켈레톤 #e5e8ef 블록, 기하 유지, 수치는 `--`
- 비활성 CTA: surface 배경 + faint 라벨 (기하 불변)
- 빈 상태: 문장 1 + 행동 1. 일러스트·이모지 금지
- 성공(소액): 하단 3초 다크 토스트 / 승인 완료: 전용 화면(M5), 토스트 금지

## 카피

- 고정 문구: "승인 전에는 외부 발송이 차단됩니다." (변경 불가)
- CTA 명령형 동사, 단정·느낌표·이모지 금지, 에러는 원인 1줄+행동 1개
- 마이크로카피는 스펙(탭별기획)의 문장을 그대로 복사 — 창작 금지
