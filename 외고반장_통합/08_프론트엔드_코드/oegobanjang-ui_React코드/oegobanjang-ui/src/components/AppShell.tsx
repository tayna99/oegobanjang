import React from 'react';
import { Bell, BriefcaseBusiness, CalendarCheck, CheckCircle, Clock3, ClipboardList, FileCheck2, MessageSquare, Search, Users, UserRoundPlus } from 'lucide-react';
import { TabKey, company } from '../data';
import { cn } from './ui';

const tabs: Array<{ key: TabKey; label: string; icon: React.ElementType }> = [
  { key: 'today', label: '오늘 할 일', icon: CalendarCheck },
  { key: 'hiring', label: '채용 준비', icon: UserRoundPlus },
  { key: 'workers', label: '근로자', icon: Users },
  { key: 'contact', label: '컨택', icon: MessageSquare },
  { key: 'cases', label: '케이스', icon: ClipboardList },
  { key: 'admin', label: '행정사 검토', icon: FileCheck2 },
  { key: 'judgment', label: '판단 기록', icon: Clock3 },
];

export function AppShell({ active, onTabChange, children }: { active: TabKey; onTabChange: (key: TabKey) => void; children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white text-slate-950">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="flex h-[58px] items-center justify-between px-7">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-black text-white">반</div>
              <div className="text-xl font-black tracking-[-0.03em]">외고반장</div>
            </div>
            <div className="h-7 w-px bg-slate-200" />
            <button className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
              <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-600 text-xs font-black text-white">한</span>
              {company.name}
              <span className="text-slate-400">· {company.location}</span>
            </button>
          </div>

          <div className="hidden w-[420px] items-center gap-2 rounded-2xl bg-slate-50 px-4 py-2.5 text-slate-400 lg:flex">
            <Search className="h-4 w-4" />
            <span className="text-sm">근로자, 케이스, 서류, 메시지 검색</span>
          </div>

          <div className="flex items-center gap-4">
            <button className="relative rounded-full p-2 hover:bg-slate-50">
              <Bell className="h-5 w-5 text-slate-700" />
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-black text-white">12</span>
            </button>
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-black text-white">김</div>
              <div className="hidden text-sm md:block">
                <div className="font-bold">{company.manager}</div>
                <div className="text-xs text-slate-500">{company.role}</div>
              </div>
            </div>
          </div>
        </div>

        <nav className="flex h-11 items-center gap-7 px-8 text-sm text-slate-500">
          {tabs.map(({ key, label, icon: Icon }) => {
            const selected = active === key;
            return (
              <button
                key={key}
                onClick={() => onTabChange(key)}
                className={cn(
                  'flex h-full items-center gap-2 border-b-2 border-transparent px-1 font-semibold transition',
                  selected && 'border-blue-700 text-blue-700'
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            );
          })}
        </nav>
      </header>

      <main className="relative min-h-[calc(100vh-102px)] px-7 py-7">{children}</main>

      <button className="fixed bottom-7 right-7 flex h-14 items-center gap-2 rounded-full bg-gradient-to-r from-blue-700 to-teal-500 px-6 text-sm font-black text-white shadow-2xl shadow-blue-200">
        <BriefcaseBusiness className="h-4 w-4" /> AI 반장
      </button>
    </div>
  );
}
