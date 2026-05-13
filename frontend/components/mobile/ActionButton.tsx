import type { ButtonHTMLAttributes, ReactNode } from "react";

export function ActionButton({
  children,
  kind = "primary",
  onClick,
  ...props
}: {
  children: ReactNode;
  kind?: "primary" | "outline" | "teal";
  onClick?: () => void | Promise<void>;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className="mobile-demo-action" data-kind={kind} onClick={onClick} type="button" {...props}>
      {children}
    </button>
  );
}
