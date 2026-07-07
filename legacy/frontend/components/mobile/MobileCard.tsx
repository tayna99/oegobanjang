import type { ComponentPropsWithoutRef, ReactNode } from "react";

export function MobileCard({
  children,
  className = "",
  ...props
}: {
  children: ReactNode;
  className?: string;
} & ComponentPropsWithoutRef<"section">) {
  return (
    <section className={`mobile-demo-card ${className}`} {...props}>
      {children}
    </section>
  );
}
