import { ClipboardCheck, FileText, Home, Settings } from "lucide-react";

const tabs = [
  { icon: Home, label: "브리핑" },
  { icon: ClipboardCheck, label: "승인" },
  { icon: FileText, label: "업무 기록" },
  { icon: Settings, label: "설정" },
];

export function BottomNav() {
  return (
    <nav className="mobile-demo-bottom-nav" aria-label="대표 모바일 하단 탭">
      {tabs.map((tab, index) => {
        const Icon = tab.icon;
        return (
          <button className={index === 0 ? "active" : ""} key={tab.label} type="button">
            <Icon aria-hidden="true" />
            <span>{tab.label}</span>
          </button>
        );
      })}
      <i aria-hidden="true" />
    </nav>
  );
}
