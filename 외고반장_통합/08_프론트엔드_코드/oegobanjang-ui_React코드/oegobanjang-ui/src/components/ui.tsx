import React from 'react';
import { ChevronRight, LucideIcon } from 'lucide-react';

export function cn(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ');
}

export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('rounded-2xl border border-slate-200 bg-white shadow-sm', className)}>{children}</div>;
}

export function Badge({ children, tone = 'blue' }: { children: React.ReactNode; tone?: 'blue' | 'green' | 'orange' | 'red' | 'gray' | 'purple' }) {
  const tones = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    gray: 'bg-slate-50 text-slate-600 border-slate-200',
    purple: 'bg-violet-50 text-violet-700 border-violet-200',
  };
  return <span className={cn('inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold', tones[tone])}>{children}</span>;
}

export function IconTile({ icon: Icon, tone = 'blue' }: { icon: LucideIcon; tone?: 'blue' | 'green' | 'orange' | 'red' | 'purple' | 'teal' }) {
  const tones = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    orange: 'bg-orange-50 text-orange-500',
    red: 'bg-red-50 text-red-500',
    purple: 'bg-violet-50 text-violet-600',
    teal: 'bg-teal-50 text-teal-600',
  };
  return <div className={cn('flex h-11 w-11 items-center justify-center rounded-xl', tones[tone])}><Icon className="h-5 w-5" /></div>;
}

export function PillButton({ children, tone = 'blue' }: { children: React.ReactNode; tone?: 'blue' | 'gray' | 'orange' | 'green' }) {
  const tones = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    gray: 'bg-slate-50 text-slate-700 border-slate-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  };
  return <button className={cn('inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-semibold hover:brightness-[.98]', tones[tone])}>{children}</button>;
}

export function Button({ children, variant = 'primary', className = '', onClick }: { children: React.ReactNode; variant?: 'primary' | 'secondary' | 'ghost'; className?: string; onClick?: () => void }) {
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-white text-slate-900 border border-slate-200 hover:bg-slate-50',
    ghost: 'bg-transparent text-slate-600 hover:bg-slate-50',
  };
  return <button onClick={onClick} className={cn('inline-flex h-10 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition', variants[variant], className)}>{children}</button>;
}

export function EmptyChevron() {
  return <ChevronRight className="h-4 w-4 text-slate-400" />;
}
