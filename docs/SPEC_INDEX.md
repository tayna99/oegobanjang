# SPEC_INDEX — 설계 문서 ↔ 구현 매핑 지도

> 원본 위치: `reference/specs/` (12_모바일퍼스트_재설계에서 복사).
> 규칙: 태스크에 명시된 문서만 읽는다. 전체 폴더 일괄 로드 금지 (토큰 낭비 + Lost-in-the-Middle).

| 스펙 문서 | 내용 | 구현 시 읽는 시점 |
|---|---|---|
| `통합설계_v1.md` | 제품 결정 D1~D6, 에이전트 런 구조("자유는 루프에, 경계는 도구에, 트리거는 이벤트에") | M0 시작 전 1회 + 런 엔진 작업 시 |
| `1단계_화면상태스펙_M1-M9_v1.md` (v1.2) | 모든 화면의 5상태·컴포넌트 props·배지 규칙 | **해당 화면 태스크마다 해당 섹션만** |
| `2단계_알림카탈로그_딥링크맵_v1.md` | 딥링크 URI 맵(§3), 알림 이벤트 | 라우터 태스크 |
| `3단계_온보딩플로우_v1.md` | O1~O5 온보딩 | M4 마일스톤 |
| `4단계_모바일디자인토큰_v1.md` | CSS 변수·타이포·터치 타깃·모션 | tokens.css 태스크 (rules/design.md가 요약본) |
| `탭별_UXUI_상세기획_v1.md` | 탭별 위계·간격·마이크로카피·이동 규칙 | 각 탭 화면 태스크 |
| `6단계_기존코드_갭분석_v1.md` | 재사용/신규 분류, 마이그레이션 4스텝 | M0~M1 (구 oegobanjang-ui 참조 시) |
| `7단계_권한모델_승인위임_v1.md` | 역할 매트릭스·위임·본인확인 | M4 마일스톤 |
| `8단계_데모시나리오_v1.md` | 데모 4막 대본 | M3 데모 폴리시 태스크 |
| `9단계_에이전틱성_비판검토_v1.md` | 프로액티브 런·오케스트레이터·자율성 사다리 | 런 엔진·프로액티브 태스크 |
| `reference/prototype_v3.html` | **UI 시각 기준 + mock 데이터 + 인터랙션 각본** | 모든 화면 태스크 (해당 섹션의 마크업 참조) |

## 프로토타입 v3에서 이식할 것

| v3의 것 | 코드로 |
|---|---|
| `:root` CSS 변수 전체 | `src/styles/tokens.css` 그대로 |
| `I={home,list,…}` SVG 아이콘 | `src/components/icons.tsx` |
| `CASE` 레지스트리 (케이스 시트 데이터) | `src/mocks/fixtures.ts` — 타입은 1단계 §0.4로 정규화 |
| `APPROVE` 승인 런 설정 | `src/mocks/runs.ts` (RunConfig[]) |
| `DRAFT` 초안 3종 (KR/VN/EN + revised) | `src/mocks/drafts.ts` |
| `EV` 이벤트 + 카테고리 | `src/mocks/evidence.ts` |
| `renderRun()` 각본 재생 로직 | `src/features/runs/runEngine.ts` (스텝 스트리밍 훅) |
| 모션 값 (430ms 스텝 간격, push-in 등) | tokens.css `--motion-*` + 컴포넌트 |
