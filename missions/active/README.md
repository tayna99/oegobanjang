# Active Missions

현재 active에는 아직 완료 검증이 닫히지 않은 mission만 둔다.

## Active

- `005-frontend-dashboard.md`
  - 상태: blocked
  - 이유: route 폴더는 존재하지만 `frontend/package.json`이 없어 build/test 명령을 확정할 수 없다.
  - 다음 작업: frontend package/runtime 기준을 정한 뒤 dashboard route, mock cards, approval/evidence 화면, build/test를 검증한다.

## Completed 처리 기준

- 구현 파일과 테스트가 존재한다.
- acceptance criteria를 현재 runtime 기준으로 만족한다.
- 자동 발송, 행정사/송출회사 자동 전달, 정부 제출을 열지 않는다.
- Evidence/approval 관련 테스트가 통과한다.
