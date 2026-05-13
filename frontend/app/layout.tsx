import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "외고반장 운영 대시보드",
  description: "외국인 고용 운영 업무를 승인과 근거 중심으로 확인하는 MVP 대시보드",
};

const navItems = [
  ["오늘 할 일", "/dashboard"],
  ["채용 준비", "/hiring"],
  ["근로자", "/workers"],
  ["컨택", "/contacts"],
  ["케이스", "/visa"],
  ["행정사 검토", "/documents"],
  ["판단 기록", "/evidence"],
  ["승인", "/approvals"],
  ["모바일", "/mobile/daily-briefing"],
] as const;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <main className="app-shell">
          <div className="role-switcher" aria-label="화면 모드">
            <span>화면</span>
            <Link className="role-pill active" href="/dashboard">
              ▭ PC · 인력 담당자
            </Link>
            <Link className="role-pill" href="/mobile/daily-briefing">
              ▯ 모바일 · 사장님
            </Link>
            <span className="role-meta">· 오늘 2026.05.13 · 한별제조 24명</span>
          </div>
          <header className="topbar">
            <Link className="brand" href="/dashboard">
              <span className="brand-icon">반</span>
              <h1 className="brand-title">외고반장</h1>
            </Link>
            <div className="company-switcher">
              <span>한</span>
              <strong>한별제조</strong>
              <small>· 경기 화성</small>
            </div>
            <label className="global-search">
              <span>⌕</span>
              <input placeholder="근로자, 케이스, 서류, 메시지 검색" />
            </label>
            <div className="user-chip">
              <span className="notification-dot">12</span>
              <span className="user-avatar">김</span>
              <strong>김대리</strong>
              <small>인사팀</small>
            </div>
          </header>
          <nav className="nav" aria-label="주요 화면">
            {navItems.map(([label, href]) => (
              <Link key={href} href={href}>
                {label}
              </Link>
            ))}
          </nav>
          {children}
        </main>
      </body>
    </html>
  );
}
