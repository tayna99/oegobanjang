# ROADMAP — 마일스톤 · 태스크 스펙 · DoD

> 태스크 1개 = Claude Code 세션 1개 크기. 순서대로. 각 태스크: 위임 레벨(L1 자율 / L2 계획 승인 / L3 협업) + 읽을 스펙 + DoD(검증 명령).
> 진행 기록은 `plans/HANDOFF.md`에 남긴다 (에이전트가 태스크 종료 시 갱신).
> 디자인 기준(2026-07-11 확정): claude.ai/design "Mobile screen design" 프로젝트의 **Montage(Wanted) 시스템** — `rules/design.md`(v2)와 `docs/DESIGN_SYNC_AUDIT_2026-07-11.md` 참조. 전환 작업은 M2.5.

## M0 — Sanity 기반 (코드보다 검증 먼저)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 0.1 | Vite+React+TS+Tailwind+router+zustand 스캐폴드, `npm run verify` 스크립트 구성 | L1 | — | `verify` 통과, 빈 앱 렌더 |
| 0.2 | `styles/tokens.css` + tailwind theme 연동 (v3 `:root` 이식) | L1 | prototype_v3, rules/design.md | 토큰 스냅샷 테스트 1개 |
| 0.3 | `src/types.ts` 데이터 타입 + `calcDday`·`maskId` 유틸 + 단위 테스트 | L1 | 1단계 §0.4 | dDay 경계값(D+, D-0, D-30, D-90) 테스트 통과 |
| 0.4 | 스토어 3종(case/approval/evidence) + **가드레일 테스트** | L2 | GOTCHAS §1·2 | "승인 없이 dispatch 불가"·"evidence append-only"·"중복 승인 차단" 테스트 통과 |
| 0.5 | mocks 이식 (v3의 CASE/DRAFT/APPROVE/EV → fixtures) | L1 | SPEC_INDEX 이식표 | typecheck 통과, PII 원문 없음 검사 |

## M1 — 셸과 승인 해피패스 (데모 3막의 뼈대)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 1.1 | 라우터+딥링크 맵, Shell(모바일 탭바/PC 헤더 분기) | L2 | 2단계 §3, 탭별기획 §0 | 라우트 스냅샷 테스트, 딥링크 백스택 = M1→목적지 |
| 1.2 | 공용 컴포넌트: Button/Badge/Card/SafetyNotice/OfflineBanner/Skeleton | L1 | 1단계 §0.2·0.3, rules/design.md | 스토리 렌더 테스트, 배지 색 규칙 테이블 테스트 |
| 1.3 | M1 브리핑 홈 (5상태 전부: default/empty/loading/error/offline) | L2 | 1단계 M1, 탭별기획 §1 | 상태별 렌더 테스트 5개, empty에 온보딩 유도 |
| 1.4 | BottomSheet + M2 케이스 시트 (데이터 구동, 케이스별 복제 금지) | L2 | 1단계 M2, GOTCHAS §4 | citation 0건 → 승인 locked 테스트 |
| 1.5 | 런 엔진 + StepTimeline (mode: approval/command/replay, 스텝 스트리밍) | **L3** | 1단계 M9 v1.2, ARCHITECTURE §5 | 스트리밍 완료 전 승인 disabled 테스트, guardrail 스텝 렌더 |
| 1.6 | M3 초안(언어 토글·수정 요청 시트) + M4 승인 + M5 완료 + 상태 전파 | L2 | 1단계 M3~M5 | **E2E: 알림딥링크→M1→M2→M3→M4→M5→M1 상태 반영** (playwright) |

## M2 — 나머지 탭 (확인 면)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 2.1 | M7 케이스 목록 (필터 칩·그룹·딥링크 프리셋) | L1 | 1단계 M7, 탭별기획 §2 | 필터·정렬 deterministic 테스트 |
| ✅ 2.2 | 메시지 탭 + 스레드 대화 뷰 + M6 응답 해석(isFinal:false→확인) — 목록 원문 미노출, 원문은 스레드 내부만 | L2 | 1단계 M6, 탭별기획 §3, 블루프린트 §9-A | 해석 확인 시 상태 갱신+evidence 테스트 |
| ✅ 2.3 | M8 판단 기록 (타임라인·필터·이벤트 상세 시트·딥링크 하이라이트) — 모바일 /evidence, audit.ts 재사용 | L1 | 1단계 M8, 탭별기획 §4 | 해시만 표시(원문 없음) 테스트 |
| ✅ 2.4 | 행정사 패키지 화면 — 대상 케이스 Batbayar(블루프린트 §3 로스터), 포함 항목 토글·검토 요청서·PII 마스킹·승인 게이트 내보내기+이력 | L1 | PC.dc.html 운영관제형 §2d, 블루프린트 §1 | 승인 흐름 단계 렌더 테스트, 내보내기 승인 게이트 테스트 |

## M2.5 — 디자인 시스템 v2(Montage) 전환 · PC 확장 화면

> 근거: `reference/design-system/외고반장 PC.dc.html`(저장소에 고정된 사본, 원본은 claude.ai/design `bd0fd8f8-615f-48e9-875b-eb5c9e9b398d` — 고정 경위는 `reference/design-system/README.md`)의 **통합 재설계(3a·3b·3c) — 사용자 확정(2026-07-11)** + `rules/design.md`(v2) + `docs/DESIGN_SYNC_AUDIT_2026-07-11.md`(매핑표 §3, 판단 §5).
> 순서: 2.2~2.4 착수 전에 2.5.1~2.5.3을 먼저 끝내는 것을 권장(신규 탭을 v2 토큰으로 바로 구현해 이중 리스킨 방지). 2.5.6은 M3 완료 후.
> 결정(2026-07-11): CSV 업로드 화면 → **4.4로 신설**(아래 M4 표). 모바일 개편안(`reference/design-system/외고반장 Mobile.dc.html` 승인 큐 중심) → **보류, M2.5 범위 밖**(사유: AUDIT §5-4).

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 2.5.1 | tokens.css v2 — Montage atomic+semantic 2계층·light/dark(`[data-theme="dark"]`) 이식, Tailwind theme `var(--color-*)` 재배선, PC 밀도 타입램프(10.5~13.5px) 토큰 등록 | L1 | rules/design.md(v2) §1·2·3, colors_and_type.css | 토큰 스냅샷 갱신, 다크 테마 스위치 렌더 테스트, Pretendard 로드 확인, PC 타입램프 임의값 0건 |
| 2.5.2 | 공용 컴포넌트 v2 — Badge→Chip 개명·severity 색표 교체, Button/Card 라디우스·아웃라인(inset box-shadow)·모션(0.2s ease) 전환 | L2 | rules/design.md(v2) §4·5 | Chip severity 색 규칙 테이블 테스트, 아웃라인 inset box-shadow 스냅샷, 기존 테스트 전건 통과 |
| 2.5.3 | 기구현 화면(M1 전체·2.1 케이스 목록) v2 리스킨 + ui-matcher 기준을 디자인 프로젝트로 교체 + rules/design.md 부록 A 삭제 | L2 | AUDIT §3 매핑표 | 1.6 E2E 통과, verify PASS, 임의 hex 0건(verifier grep) |
| 2.5.4 | PC 케이스 워크벤치(3b, 3열: 목록·상세·AI 패널) — Shell lg+ 레이아웃 확장, 기존 라우트·스토어 재사용 | L2 | `reference/design-system/외고반장 PC.dc.html` §3b, 탭별기획 §2 | 3열 렌더·목록↔상세 동기 테스트, 모바일 회귀 없음 |
| 2.5.4b | **Design-first 파운데이션** — 6인 로스터 치환·모델 확장(team/담당/caseCode/체류만료/근거 완성도/agentStage)·중앙 citationStore(id·status·F등급)·EvidenceType 3종(+해시 시드 #4783~91)·토큰 2쌍(draft 보라/detected 시안)+.43 계층·컴포넌트 킷 6종 정합 | L2 | 블루프린트 §3·§4, `Montage 공용 컴포넌트.dc.html` | 기존 테스트 전건(로스터 반영 개정), returned 전이·케이스 단위 승인·F등급 사용 불가 가드레일 테스트, Chip draft/detected 색표 테스트 |
| ✅ 2.5.5 | PC 거버넌스(3c) — 근거 라이브러리(중앙 스토어·KPI 파생·연계 케이스·F등급)·감사 로그(필터·해시·INSERT-only) | L2 | `외고반장 PC.dc.html` §3c, 탭별기획 §4, 블루프린트 §3 — **선행: 2.5.4b** | 내보내기 산출물 해시만(원문 없음) 테스트, 라이브러리 KPI=스토어 파생값 |
| ✅ 2.5.6 | PC 컨트롤 타워(3a) — 파이프라인·KPI·우선 처리 큐·활동/감사 레일 (파이프라인 델타·주간 추이는 mock, 실집계는 M3 데이터로 교체) | L3 | `외고반장 PC.dc.html` §3a, 9단계 P0, 블루프린트 §2(C10: 고위험 행 액션은 "검토") | 큐 정렬(위험×D-day) deterministic 테스트, KPI=스토어 파생값 |

## M2.6 — 모바일 승인 큐 개편 (Mobile.dc.html 2a~2d 채택)

> 근거: `reference/design-system/외고반장 Mobile.dc.html` + `docs/DESIGN_FIRST_BLUEPRINT_2026-07-11.md`(§1 채택 맵·§2 교정 3건·§5 라우팅). 2026-07-11 사용자 지시로 기존 '보류'를 대체. **선행: 2.5.4b.**
> 데모 대본(8단계 3막) 개정 필요 — 스트리밍 게이트 → 체크리스트 게이트(블루프린트 §2). 사용자 확인 항목.

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| 2.6.1 | M1 브리핑 홈 개편(2a): 파이프라인 스탯 로우·"내가 처리할 승인 N건" 카드(단일 "검토" CTA)·"에이전트 진행 중" 리스트 — 커맨드바 존치 | L2 | Mobile.dc.html §2a, 블루프린트 §1 | 2a 카피 렌더 테스트, 카드 CTA 1개 테스트, 기존 5상태 테스트 개정 통과 |
| 2.6.2 | 케이스 상세 전면 페이지(2b): 바텀시트 대체 — 왜 확인·누락 서류·연결 근거·초안 VN/KR·"검토 계속" | L2 | Mobile.dc.html §2b | 전면 페이지 렌더, 검토 계속→승인 페이지 이동 테스트, PC 워크벤치 회귀 없음 |
| 2.6.3 | 승인 체크리스트 페이지(2c): 필수 4항목 게이트·의견/반려 사유·승인/반려(returned 전이) — 배너 문구는 정본 교정(C1) | L2 | Mobile.dc.html §2c, 블루프린트 §2 | 체크리스트 미완 시 승인 disabled, citation-0 잠금 유지, 반려 사유 evidence 기록 테스트, E2E(1.6) 개편 흐름 갱신 |
| 2.6.4 | 승인 이력 페이지(2d): `/case/:id/history` 신설 — 6노드 타임라인·해시·소요시간, 노드 색은 §4.2 정본(C9: 사람 결정만 primary) | L2 | Mobile.dc.html §2d, 탭별기획 §4.2 | 사람 결정 노드만 primary 테스트, 해시만 표시(원문 없음) 테스트 |

## M3 — 에이전틱 차별화 (9단계 P0)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 3.1 | 프로액티브 런: 이벤트→자동 런→카드 `preparedBy:'agent'`+재생 뷰 | **L3** | 9단계 P0-1, 1단계 v1.2 | 재생 뷰 읽기 전용, 가드레일 정지 스텝 존재 테스트 (재생 #4788에 발송 전 정지 스텝 추가) |
| ✅ 3.2 | 커맨드 바 → M9 사용자 런 → 결과 카드 → 케이스 연결 | L2 | 1단계 M9 | 런 1건=evidence 1건 테스트 (결과 카드 처리 대상 케이스→nav.toCase) |
| ✅ 3.3 | 케이스 에이전트 활동 타임라인(런 체이닝)+nextWake | L2 | 9단계 P0-2 | 체인 렌더 테스트 (타임라인 판단 기록 #→재생 런 진입) |
| ✅ 3.4 | 데모 폴리시: 8단계 4막 대본 그대로 시연 가능 상태 점검 | L1 | 8단계 | 데모 체크리스트 전 항목 수동 확인 + E2E 스모크 (demoScript.test 4막 스모크 + 커맨드 런 가드레일 스텝 추가) |

## M4 — 온보딩·권한 (파일럿 준비)

| # | 태스크 | 레벨 | 스펙 | DoD |
|---|---|---|---|---|
| ✅ 4.1 | 온보딩 O1~O5 (수기 4필드 → 첫 브리핑 동기 생성 연출) | L2 | 3단계 | E2E: 근로자 1명 등록→첫 카드 도달 — `src/features/onboarding/OnboardingFlow.tsx`(Shell 바깥 형제 라우트 `/onboarding`), `lib/onboarding.ts`(완료 시 로스터 시드+evidence) |
| ✅ 4.2 | 역할 분기(owner/manager 홈·권한 가드) | L2 | 7단계 §2·6 | 라우트 가드 테스트 (owner의 M9 쓰기 도구 차단) — roleStore + Shell 토글, visibleCardsForRole 연결, RunPage 라우트 가드 |
| ✅ 4.3 | 승인 본인확인 목업(PIN) + 대리 승인 배지 | L2 | 7단계 §3·4 | 승인 이벤트에 결정자·본인/대리 기록 — ApprovePage PIN 시트(고정 데모값+불일치 재시도) + 대리 체크박스, evidence actor "OO (본인 확인 완료)"/"OO (대리 승인 · 위임: 김대표)" |
| ✅ 4.4 | CSV 일괄 업로드(PC) — 근로자 대량 등록, 4.1 온보딩과 동일 데이터 계약 공유 | L2 | 통합설계 D4·D6, 8단계 E4 | 잘못된 행(헤더 누락·중복 사번) 검증 실패 테스트, 성공 시 근로자 N명 스토어 반영 테스트 — `lib/csvUpload.ts`(validateRows/rowsToCards), `CsvUploadPage`/`CsvUploadWorkbench`(`/cases/import`, 담당자 전용), CaseWorkbench 좌측 레일 진입 버튼 |

## ✅ 4.2/4.3 확장 — 운영급 RBAC(7단계 권한모델·승인위임 전체)

4.2/4.3의 MVP 축소판(owner/manager 2역할, 체크박스식 대리) 이후 사용자 지시로
`reference/specs/7단계_권한모델_승인위임_v1.md` 전체를 구현했다. **목업 없이 진행** —
근거는 3개 Explore + 1개 Plan 에이전트가 실제 파일(PC/Mobile .dc.html, 기존 컴포넌트)을
대조 검증: 설정/구성원/위임/정책 화면은 전부 기존 채택 패턴(행 목록·세그먼트 버튼·체크박스)
으로 조립 가능했고, 행정사 링크는 이미 얼어붙은 PC §2d 콘텐츠의 상태 확장이었다
(블루프린트 §9.1-A와 동일 논리 — 자세한 판단 근거는 Phase A~D 커밋 메시지 참조).

| Phase | 내용 | 커밋 |
|---|---|---|
| A | Role 3종(manager/owner/viewer) + EvidenceType 9종(§5) + CompanyMember/DelegationConfig/ApprovalPolicy + companyStore + M8 역할 라벨 접두 | f4258eb |
| B | 기존 화면(M1~M4) 역할 매트릭스 반영 — owner 통계 숨김·M2 액션바 분기·정책 기반 "대표 승인 요청"·공동대표 배너·viewer 라우트 가드 | 166360f |
| C | 설정 화면 3종 신설(구성원 관리·위임 관리·승인 정책), system-derived 태깅 첫 실행(기존 M6/M8/M9/커맨드바도 backfill) | 174a0ec |
| D | 행정사 패키지 링크 만료(7일)·재발급·열람 로그 + 무인증 라우트(`/link/:packageId`) + 자동 에스컬레이션 프리시드("승인 지연" Chip) | 7de28f7 |

**의도적으로 다루지 않은 것**(스펙 §7 "미해결 → 후속"과 동일 — 후속 파일럿 피드백 이후):
- viewer의 M8 PII 마스킹 수준 차등, expert 화이트라벨 모드, 승인 정책 케이스유형별 세분화.
- 공동대표 배너는 메커니즘 구현+테스트 완료(Phase B)이나, 6인 활성 로스터를 건드리는
  영구 프리셋 케이스는 추가하지 않음(기존 승인 대기 카운트 테스트·8단계 데모 대본 보존).
- 48h/72h 실시간 에스컬레이션 타이머 — 백엔드·다중 세션이 없어 물리적으로 불가능,
  RunEngine 각본 철학과 동일하게 프리시드 evidence로 대체.
- companyStore.approvalPolicy 기본값은 스펙상 "정답"인 owner_only 대신 manager_allowed —
  owner_only를 기본값으로 두면 이미 확립된 8단계 데모 대본·approvalFlow.test.tsx 대부분이
  즉시 "대표 승인 요청"으로 바뀌어 깨진다(설정 화면에서 owner_only로 전환해 그 분기 시연 가능).

## M4.5 — 온보딩·CSV 목업 확보 + PC 역할 기반 신규 화면(2026-07-13)

4.1(온보딩)·4.4(CSV)는 B-tier(design-then-freeze)로 목업 없이는 블록 상태였다(브리프는
`reference/design-system/design-briefs/`에 선작성). 2026-07-13, 사용자가 두 브리프를
claude.ai/design에 투입해 목업을 생성하고 `외고반장 PC.dc.html`도 재수입 — 재수입판은
역할 기반 신규 PC 화면 6종(4a~4f)을 기존 3a~3c/2a~2d/v1 앞에 추가한 형태였다. 감사:
`docs/DESIGN_SYNC_AUDIT_2026-07-13.md`(정합 우수, 마스킹 형식 1건 불일치 — 전체 마스킹
유지로 확정). 사용자 결정으로 **4a~4f 신규 PC 화면까지 이번 스코프에 전부 포함**한다.

| # | 태스크 | 분류 | 근거·비고 |
|---|---|---|---|
| ✅ 4.1 | 온보딩 O1~O5 | 완료 | 목업: `외고반장 온보딩.dc.html`. 단일 상태머신 컴포넌트(6단계) + Shell 바깥 형제 라우트. 외국인등록번호는 목업의 부분 마스킹 대신 `maskId()` 전체 마스킹 채택(§2 결함 판정). |
| ✅ 4.4 | CSV 일괄 업로드 | 완료 | 목업: `외고반장 CSV 업로드.dc.html`. 실제 Shell 크롬(64px) 위 4단계(대기→검증→결과→완료), 외국인등록번호는 전체 마스킹(목업의 부분 마스킹 미채택). |
| ✅ 4.5a | PC 케이스 테이블 보강(4a) | 부분 확장 완료 | `CaseWorkbench.tsx` 목록 행에 담당·서류 준비율(N/M) 노출 추가. **프리셋 필터 5종은 미채택** — 기존 `CASE_FILTERS`(전체/즉시확인/우선확인/확인필요/승인대기)가 모바일 `CaseListScreen`과 공유돼 교체 시 파급 범위가 크고 별도 IA 결정이 필요해 이번 스코프에서 제외(§3 델타표에 이미 명시된 "부분" 범위). |
| ✅ 4.5b | PC 근로자 데이터 관리(4b) | 순신규 완료 | `/cases/workers`(담당자 전용) — 근로자 목록(workerRef 있는 CaseCard 전체, 워커 전용 엔티티 없음) + CSV 가져오기 진입점(4.4 연동) + 서류스캔은 정적 "준비 중" 카드(OCR 파이프라인 없음, 순신규 분류) |
| ✅ 4.5c | PC 메시지 데스크톱 분기(4c) | 부분 확장 완료 | `MessagesPage`에 `useIsDesktop` 분기 추가 → `MessagesWorkbench`(스레드 목록·대화·연결 케이스 3열). M6 해석확인 로직은 ThreadPage(모바일)와 별도 구현(CaseWorkbench/CaseReviewPage 관계와 동일 원칙 — 공유 데이터층, 플랫폼별 프레젠테이션). |
| 4.5d | PC 발송 실행 큐(4d) | 순신규 | mock dispatch, 신규 EvidenceType `dispatch_executed`/`delivery_confirmed` |
| 4.5e | 행정사 패키지 구조화된 회신(4e 확장) | 확장 | Phase D 위에 회신 폼(보완요청/검토완료/질문) + `package_reply` evidence |
| 4.5f | 사장님 PC 최소화면(4f) | 부분 확장 | 월간 리포트(정적 목데이터) + "승인은 모바일에서" 배너 |

**PC 나비 IA 결정**: 목업은 최상위 탭 7개(컨트롤타워/케이스/근로자/메시지/발송실행/거버넌스/설정)를
가정하지만 실제 Shell은 5개뿐(`Shell.tsx:11-17`) — 근로자·발송실행은 새 최상위 탭이 아니라
**케이스 하위 화면**으로 구현한다(컨트롤타워/거버넌스가 이미 브리핑/기록 데스크톱 분기로 들어가
있는 것과 동일 패턴). 이 IA 재정렬 자체는 계속 미결로 남긴다(2.5.6 HANDOFF에서부터 미결 기록).

## 백엔드 접속점 (이후 — 별도 계획)

- mockApi → FastAPI(기존 Daily Briefing PRD 백엔드)로 교체. 계약: `src/types.ts` = PRD §11 Data Contracts
- runEngine 각본 → LangGraph createAgent 스트리밍으로 교체 (RunConfig 인터페이스 유지)
- 발송 어댑터·알림톡은 계속 범위 밖 (승인 기반 어댑터, PRD Sprint 6)
