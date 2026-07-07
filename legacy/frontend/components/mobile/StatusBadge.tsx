import type { ReactNode } from "react";

export function StatusBadge({
  children,
  tone = "blue",
}: {
  children: ReactNode;
  tone?: "blue" | "danger" | "teal" | "muted";
}) {
  return (
    <span className="mobile-demo-badge" data-tone={tone}>
      {children}
    </span>
  );
}
