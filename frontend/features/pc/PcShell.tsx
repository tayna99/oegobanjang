"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  BriefcaseBusiness,
  CalendarCheck,
  ClipboardList,
  Clock3,
  FileCheck2,
  MessageSquare,
  Search,
  UserRoundPlus,
  Users,
} from "lucide-react";
import { company, type PcViewKey } from "./data";
import { cn } from "./ui";
import styles from "./PcShell.module.css";
import {
  AdminReviewView,
  CasesView,
  ContactView,
  HiringPreparationView,
  JudgmentLogView,
  TodayTasksView,
  WorkersView,
} from "./views";

const routes: Array<{ key: PcViewKey; href: string; label: string; icon: React.ElementType }> = [
  { key: "today", href: "/dashboard", label: "오늘 할 일", icon: CalendarCheck },
  { key: "hiring", href: "/hiring", label: "채용 준비", icon: UserRoundPlus },
  { key: "workers", href: "/workers", label: "근로자", icon: Users },
  { key: "contact", href: "/contacts", label: "컨택", icon: MessageSquare },
  { key: "cases", href: "/visa", label: "케이스", icon: ClipboardList },
  { key: "admin", href: "/documents", label: "행정사 검토", icon: FileCheck2 },
  { key: "judgment", href: "/evidence", label: "판단 기록", icon: Clock3 },
];

const pathToView: Record<string, PcViewKey> = {
  "/dashboard": "today",
  "/hiring": "hiring",
  "/workers": "workers",
  "/contacts": "contact",
  "/visa": "cases",
  "/documents": "admin",
  "/evidence": "judgment",
};

function renderView(view: PcViewKey) {
  if (view === "hiring") return <HiringPreparationView />;
  if (view === "workers") return <WorkersView />;
  if (view === "contact") return <ContactView />;
  if (view === "cases") return <CasesView />;
  if (view === "admin") return <AdminReviewView />;
  if (view === "judgment") return <JudgmentLogView />;
  return <TodayTasksView />;
}

export function PcShell() {
  const pathname = usePathname();
  const activeView = pathToView[pathname] ?? "today";

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.topbar}>
          <div className={styles.leftCluster}>
            <Link className={styles.brand} href="/dashboard" aria-label="외고반장 대시보드">
              <span className={styles.brandMark}>반</span>
              <span className={styles.brandName}>외고반장</span>
            </Link>
            <span className={styles.divider} aria-hidden />
            <button className={styles.company} type="button">
              <span className={styles.companyMark}>한</span>
              {company.name}
              <span className={styles.muted}>· {company.location}</span>
            </button>
          </div>

          <div className={styles.search} aria-label="검색">
            <Search size={16} />
            <span>근로자, 케이스, 서류, 메시지 검색</span>
          </div>

          <div className={styles.rightCluster}>
            <button className={styles.iconButton} type="button" aria-label="알림">
              <Bell size={20} />
              <span className={styles.noticeCount}>12</span>
            </button>
            <div className={styles.person}>
              <span className={styles.avatar}>김</span>
              <span>
                <span className={styles.manager}>{company.manager}</span>
                <span className={styles.role}>{company.role}</span>
              </span>
            </div>
          </div>
        </div>

        <nav className={styles.nav} aria-label="PC 주요 메뉴">
          {routes.map(({ key, href, label, icon: Icon }) => (
            <Link
              key={key}
              className={cn(styles.navItem, activeView === key && styles.navItemActive)}
              href={href}
              aria-current={activeView === key ? "page" : undefined}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </nav>
      </header>

      <main className={styles.main}>{renderView(activeView)}</main>

      <button className={styles.fab} type="button">
        <BriefcaseBusiness size={16} /> AI 반장
      </button>
    </div>
  );
}
