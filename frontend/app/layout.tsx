import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "외고반장 운영 대시보드",
  description: "외국인 고용 운영 업무를 승인과 근거 중심으로 확인하는 MVP 대시보드",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
