import type { ReactNode } from "react";

export function ActionButton({
  children,
  kind = "primary",
  onClick,
}: {
  children: ReactNode;
  kind?: "primary" | "outline" | "teal";
  onClick?: () => void | Promise<void>;
}) {
  return (
    <button className="mobile-demo-action" data-kind={kind} onClick={onClick} type="button">
      {children}
    </button>
  );
}
