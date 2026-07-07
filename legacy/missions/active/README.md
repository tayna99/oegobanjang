# Active Missions

현재 active에는 아직 완료 검증이 닫히지 않은 mission만 둔다.

## Active

- `005-frontend-dashboard.md`
  - 상태: active
  - 이유: `frontend/package.json`과 Next.js runtime 기준이 존재하며 `npm run test`는 `tsc --noEmit`로 확인된다.
  - 다음 작업: PC/모바일 UI 확장, CSV 운영 화면, 근로자 상세, build/test/browser 검증을 현재 화면 기준으로 닫는다.

## Completed 처리 기준

- 구현 파일과 테스트가 존재한다.
- acceptance criteria를 현재 runtime 기준으로 만족한다.
- 자동 발송, 행정사/송출회사 자동 전달, 정부 제출을 열지 않는다.
- Evidence/approval 관련 테스트가 통과한다.
