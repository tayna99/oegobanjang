import type { ReactNode } from "react";
import { Bell, CalendarDays, ChevronLeft } from "lucide-react";
import { BottomNav } from "./BottomNav";

type TabId = "home" | "workers" | "contact" | "cases" | "more";

export function MobileShell({
  activeTab = "home",
  children,
  onTabChange,
}: {
  activeTab?: TabId;
  children: ReactNode;
  onTabChange?: (id: TabId) => void;
}) {
  return (
    <div className="mobile-demo-phone">
      <PhoneStatusBar />
      {children}
      <BottomNav activeTab={activeTab} onTabChange={onTabChange} />
    </div>
  );
}

export function PhoneStatusBar() {
  return (
    <div className="mobile-demo-statusbar" aria-hidden="true">
      <span>9:41</span>
      <div>
        <span className="mobile-demo-signal" />
        <span>⧳</span>
        <span className="mobile-demo-battery" />
      </div>
    </div>
  );
}

export function BrandHeader({ noticeCount = 0 }: { noticeCount?: number }) {
  return (
    <div className="mobile-demo-brand">
      <span className="mobile-demo-brand-mark" aria-hidden="true">만</span>
      <strong>외고반장</strong>
      <div style={{ flex: 1 }} />
      <span style={{ position: "relative", display: "inline-flex", padding: 4 }}>
        <Bell size={22} color="var(--semantic-label-neutral)" aria-hidden="true" />
        {noticeCount > 0 ? (
          <span
            aria-label={`알림 ${noticeCount}건`}
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              minWidth: 15,
              height: 15,
              borderRadius: 999,
              background: "#EF4444",
              color: "#fff",
              fontSize: 9,
              fontWeight: 700,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {noticeCount}
          </span>
        ) : null}
      </span>
    </div>
  );
}

export function PageTitle({
  back,
  date,
  onBack,
  title,
}: {
  back?: boolean;
  date?: string;
  onBack?: () => void;
  title: string;
}) {
  return (
    <div className="mobile-demo-title">
      <div>
        {back ? (
          <button aria-label="뒤로" onClick={onBack} type="button">
            <ChevronLeft size={22} aria-hidden="true" />
          </button>
        ) : null}
        <h1>{title}</h1>
      </div>
      {date ? (
        <span>
          <CalendarDays aria-hidden="true" />
          {date}
        </span>
      ) : null}
    </div>
  );
}
