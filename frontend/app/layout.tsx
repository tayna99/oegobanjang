import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "외고반장 운영 대시보드",
  description: "외국인 고용 운영 업무를 승인과 근거 중심으로 확인하는 MVP 대시보드",
};

const navItems = [
  ["대시보드", "/dashboard"],
  ["근로자", "/workers"],
  ["인력확보", "/hiring"],
  ["비자", "/visa"],
  ["서류", "/documents"],
  ["연락", "/contacts"],
  ["승인", "/approvals"],
  ["Evidence", "/evidence"],
] as const;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <main className="app-shell">
          <header className="topbar">
            <Link className="brand" href="/dashboard">
              <span className="brand-mark">WORKBRIDGE OS</span>
              <h1 className="brand-title">외고반장</h1>
            </Link>
            <nav className="nav" aria-label="주요 화면">
              {navItems.map(([label, href]) => (
                <Link key={href} href={href}>
                  {label}
                </Link>
              ))}
            </nav>
          </header>
          {children}
        </main>
      </body>
    </html>
  );
}
