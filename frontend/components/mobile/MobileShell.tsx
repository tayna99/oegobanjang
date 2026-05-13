import type { ReactNode } from "react";
import { CalendarDays, ShieldCheck } from "lucide-react";

import { BottomNav } from "./BottomNav";

export function MobileShell({ children }: { children: ReactNode }) {
  return (
    <div className="mobile-demo-phone">
      <PhoneStatusBar />
      {children}
      <BottomNav />
    </div>
  );
}

export function PhoneStatusBar() {
  return (
    <div className="mobile-demo-statusbar" aria-hidden="true">
      <span>9:41</span>
      <div>
        <span className="mobile-demo-signal" />
        <span>⌁</span>
        <span className="mobile-demo-battery" />
      </div>
    </div>
  );
}

export function BrandHeader() {
  return (
    <div className="mobile-demo-brand">
      <span>
        <ShieldCheck aria-hidden="true" />
      </span>
      <strong>AI 반장</strong>
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
            ←
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
