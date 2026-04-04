"use client";

import type { TabType } from "@/app/lib/types";

const TABS: { key: TabType; label: string }[] = [
  { key: "points", label: "PTS" },
  { key: "rebounds", label: "REB" },
  { key: "assists", label: "AST" },
  { key: "parlays", label: "PARLAYS" },
  { key: "record", label: "RECORD" },
];

interface NavbarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export default function Navbar({ activeTab, onTabChange }: NavbarProps) {
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric", year: "numeric",
  });

  return (
    <nav className="flex items-center justify-between px-4 py-3 bg-tv-bg-secondary border-b border-tv-border">
      <div className="flex items-center gap-2">
        <span className="text-tv-blue font-bold text-lg tracking-tight">EB</span>
        <span className="text-tv-text font-semibold text-sm hidden sm:inline">NBA Predictor</span>
      </div>
      <div className="flex gap-1">
        {TABS.map((tab) => (
          <button key={tab.key} onClick={() => onTabChange(tab.key)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-tv-blue text-white"
                : "bg-tv-bg-tertiary text-tv-text-secondary hover:text-tv-text"
            }`}>
            {tab.label}
          </button>
        ))}
      </div>
      <div className="text-tv-text-secondary text-xs hidden md:block">{today}</div>
    </nav>
  );
}
