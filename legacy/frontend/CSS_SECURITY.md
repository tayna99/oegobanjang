# CSS 보안 가이드

## postcss XSS 취약점 (GHSA-qx2v-qp2m-jg93)

현재 next@16.2.6이 postcss@8.4.31에 의존하고 있으며, CSS stringify 중에 `</style>` 태그가 제대로 escape되지 않을 수 있는 취약점이 있습니다.

## 보완 전략

### 1. Content Security Policy (CSP)
✅ **구현됨** - next.config.mjs에 CSP 헤더 추가
- XSS 공격 방어
- 신뢰할 수 없는 소스에서 스타일 로드 차단

### 2. 동적 스타일 생성 시 주의사항

**❌ 피해야 할 방법:**
```tsx
// 사용자 입력을 직접 CSS에 포함
const style = `color: ${userInput}`;
```

**✅권장 방법:**
```tsx
// CSS 변수 사용
<div style={{ '--user-color': userInput } as React.CSSProperties}>

// Inline 스타일 객체 사용 (자동 escape)
<div style={{ color: userInput }}>
```

### 3. 체크리스트

동적 스타일을 생성할 때:
- [ ] 사용자 입력을 CSS 문자열에 직접 포함하지 않기
- [ ] CSS-in-JS 라이브러리 사용 시 공식 문서 확인
- [ ] 입력값 검증 (색상, 길이 등 화이트리스트)
- [ ] 브라우저 개발자 도구에서 XSS 확인

## 업그레이드 계획

- next@16.3.0 정식 릴리스 시 업그레이드 (포함된 postcss 최신화)
- npm audit 모니터링

## 참고

- [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93)
- [Next.js Security Best Practices](https://nextjs.org/docs/advanced-features/security-headers)
- [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
