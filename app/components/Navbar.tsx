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
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <nav className="h-12 bg-bg-header border-b border-border-default flex items-center justify-between px-5 sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <span
          className="font-code text-lg font-bold text-t-green"
          style={{ textShadow: "0 0 12px rgba(0,255,102,0.3)" }}
        >
          EB
        </span>
        <span className="font-ui text-sm text-text-secondary hidden sm:inline">
          NBA Predictor
        </span>
      </div>

      <div className="flex h-full">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={`px-4 h-full font-code text-xs font-semibold tracking-[0.1em] uppercase transition-colors border-b-2 cursor-pointer ${
              activeTab === tab.key
                ? "text-text-primary border-t-green"
                : "text-text-secondary border-transparent hover:text-text-primary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="font-code text-xs text-text-secondary hidden md:block">
        {today}
      </div>
    </nav>
  );
}
