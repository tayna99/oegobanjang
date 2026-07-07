# HANDOFF — 세션 인수인계 기록

> 규칙: 태스크를 끝내거나 컨텍스트 40%에 도달해 세션을 넘길 때, 에이전트가 아래 형식으로 **맨 위에** 추가한다.
> 새 세션의 첫 행동: 이 파일의 최신 항목 1개 + ROADMAP의 다음 태스크를 읽는 것. (전체 히스토리 로드 금지)

---

## 형식

```
### [날짜] 태스크 번호 — 상태 (완료/중단)
- 한 일:
- 남은 일 / 중단 지점:
- 결정 사항 (다음 세션이 알아야 할 것):
- verify 상태: PASS/FAIL(원인)
- 지도/규칙 갱신: (했으면 무엇을)
```

---

(아직 기록 없음 — M0.1부터 시작)
---

### [2026-07-07] 세션 2.1 완료
- M7 케이스 목록을 `/cases`에 연결하고 필터 칩, 딥링크 프리셋(`?filter=crit|warn|info|approval`), 고정 그룹 순서(승인 대기→즉시 확인→확인 필요→예정→완료 접힘)를 구현했다.
- 필터/그룹/정렬 로직은 `src/lib/cases.ts` selector로 분리했고, 화면은 `src/features/cases/`에 `CaseListPage`/`CaseListScreen`으로 추가했다.
- compact case item은 CTA 없이 케이스 상세(`/case/:caseId`)로 진입한다.
- verify 상태: PASS(`npm run test:run -- src/lib/cases.test.ts src/features/cases/CaseListPage.test.tsx`), 전체 `npm run verify`는 별도 최종 검증에서 확인.
- 다음 세션 시작점: ROADMAP 2.2 메시지 탭 + 스레드 대화 뷰 + M6 응답 해석.
- 지속 규칙 갱신: M7 필터·정렬 로직은 컴포넌트가 아니라 `src/lib/cases.ts` selector를 기준으로 유지한다.
