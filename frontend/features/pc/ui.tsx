import type { LucideIcon } from "lucide-react";
import type { Tone } from "./data";
import styles from "./PcShell.module.css";

export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

const toneClasses: Record<Tone, string> = {
  blue: styles.toneBlue,
  green: styles.toneGreen,
  orange: styles.toneOrange,
  red: styles.toneRed,
  gray: styles.toneGray,
  purple: styles.tonePurple,
  teal: styles.toneTeal,
};

const textToneClasses: Record<Tone, string> = {
  blue: styles.textBlue,
  green: styles.textGreen,
  orange: styles.textOrange,
  red: styles.textRed,
  gray: styles.textGray,
  purple: styles.textPurple,
  teal: styles.textTeal,
};

export function toneClass(tone: Tone) {
  return toneClasses[tone];
}

export function textToneClass(tone: Tone) {
  return textToneClasses[tone];
}

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn(styles.card, className)}>{children}</div>;
}

export function Badge({ children, tone = "blue" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={cn(styles.badge, toneClass(tone))}>{children}</span>;
}

export function PillButton({ children, tone = "blue" }: { children: React.ReactNode; tone?: Tone }) {
  return <button className={cn(styles.pill, toneClass(tone))} type="button">{children}</button>;
}

export function Button({ children, variant = "primary", className }: { children: React.ReactNode; variant?: "primary" | "secondary" | "ghost"; className?: string }) {
  return <button className={cn(styles.button, variant === "primary" && styles.buttonPrimary, variant === "ghost" && styles.buttonGhost, className)} type="button">{children}</button>;
}

export function IconTile({ icon: Icon, tone = "blue" }: { icon: LucideIcon; tone?: Tone }) {
  return <span className={cn(styles.tile, toneClass(tone))}><Icon aria-hidden size={20} /></span>;
}
