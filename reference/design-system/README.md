# 디자인 시스템 원본 고정 (frozen 2026-07-11)

> **왜 이 폴더가 있는가**: M2.5 전환 전까지 저장소의 디자인 기준이 claude.ai/design "Mobile screen design" 프로젝트(`bd0fd8f8-615f-48e9-875b-eb5c9e9b398d`)라는 **외부 라이브 링크**에만 의존했다. 그 프로젝트가 수정·삭제되거나 접근 권한이 바뀌면 `rules/design.md`·`ROADMAP.md`(2.5.4~2.5.6)·`ui-matcher.md`가 가리키는 스펙이 통째로 사라진다. 이 폴더는 그 프로젝트에서 실제로 사용한 원본 파일을 **그대로, 재현 가능하게** 저장소에 고정한 것이다. 이후 디자인 결정에 대한 근거는 여기 파일을 1차로 삼는다.

## 내용물

| 파일 | 출처(프로젝트 내 경로) | 용도 |
|---|---|---|
| `montage-wanted/colors_and_type.css` | `_ds/montage-wanted-design-system-.../colors_and_type.css` | Montage(Wanted) 디자인 시스템의 원본 CSS 커스텀 프로퍼티. `src/styles/tokens.css`는 이 파일의 값을 그대로 이식한 것(§3 매핑표는 `docs/DESIGN_SYNC_AUDIT_2026-07-11.md`). 저장소에 이미 있던 `외고반장_통합/09_배포_패키지/.../colors_and_type.css` 사본과 대조해 **내용 100% 일치**(줄바꿈 문자만 다름, sha256 비교로 확인) — 드리프트 없음.
| `montage-wanted/source-rules-design.md` | 프로젝트 `rules/design.md` | 디자인 프로젝트가 자체적으로 정의한 적용 규칙 원문. **이 저장소의 `rules/design.md`(v2)는 이 파일을 바탕으로 우리 프로젝트 규칙(부록·이행 배너 등)을 얹어 각색한 것**이다 — 원문과 각색본을 구분해 추적할 수 있게 둘 다 남긴다.
| `외고반장 PC.dc.html` | 프로젝트 루트 `외고반장 PC.dc.html` | PC 디자인 3안 원본(통합 재설계 3a·3b·3c / 운영 관제형 2a~2d / v1 프로토타입). ROADMAP **2.5.4~2.5.6**(PC 케이스 워크벤치·거버넌스·컨트롤 타워)의 1차 스펙 — 지금까지는 이 경로 없이 라이브 프로젝트만 가리켰다. `docs/DESIGN_SYNC_AUDIT_2026-07-11.md` §5의 판단(통합 재설계 채택)이 바로 이 파일 내용에 근거한다.
| `외고반장 Mobile.dc.html` | 프로젝트 루트 `외고반장 Mobile.dc.html` | 모바일 개편안(승인 큐 중심) 원본. 검수 결과 **채택 보류**(`docs/DESIGN_SYNC_AUDIT_2026-07-11.md` §5-4) — 참고용으로 고정만 해둔다. `.claude/agents/ui-matcher.md`의 대조 기준이 아니다.

## 고정 방식 · 한계

- claude.ai/design MCP(`DesignSync` 도구)의 `get_file`로 2026-07-11에 가져온 내용을 그대로 저장했다 — 사람이 손으로 편집하지 않았다.
- 이 파일들은 **읽기 전용 스냅샷**이다. 디자인 프로젝트가 이후 바뀌어도 여기는 자동으로 갱신되지 않는다 — 디자인이 실제로 바뀌면 다시 `get_file`로 받아 이 폴더를 갱신하고, 갱신 날짜와 무엇이 바뀌었는지를 이 README와 `plans/HANDOFF.md`에 남긴다.
- `.dc.html` 파일은 `<x-dc>` 캔버스 마크업(디자인 도구 전용 포맷)이라 브라우저에서 그대로 열어도 실제 프로덕션 렌더링과 다를 수 있다 — 값·구조 참고용이며, 실행 가능한 프로토타입은 아니다.
