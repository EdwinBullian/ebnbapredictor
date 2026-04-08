"use client";

import { useState } from "react";
import type { Game } from "@/app/lib/types";

interface GamesSidebarProps {
  games: Game[];
  selectedGame: string | null;
  onGameSelect: (gameId: string | null) => void;
}

export default function GamesSidebar({
  games,
  selectedGame,
  onGameSelect,
}: GamesSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="fixed right-0 top-16 bg-bg-surface border border-border-default px-2 py-3 text-text-secondary text-xs hover:text-text-primary z-20 cursor-pointer"
      >
        &#9664; {games.length}G
      </button>
    );
  }

  return (
    <aside className="w-56 shrink-0 bg-bg-surface border-l border-border-default overflow-y-auto hidden lg:block">
      <div className="flex items-center justify-between px-4 pt-3.5 pb-2">
        <span className="font-code text-[11px] font-semibold tracking-[0.1em] uppercase text-text-secondary">
          Today&apos;s Games
        </span>
        <button
          onClick={() => setCollapsed(true)}
          className="text-text-muted hover:text-text-secondary text-xs cursor-pointer"
        >
          &#9654;
        </button>
      </div>

      <button
        onClick={() => onGameSelect(null)}
        className={`w-full text-left px-4 py-1.5 font-code text-xs cursor-pointer ${
          selectedGame === null
            ? "text-t-green"
            : "text-text-secondary hover:text-text-primary"
        }`}
      >
        All Games
      </button>

      <div className="mt-1">
        {games.map((game) => {
          const isSelected = selectedGame === game.game_id;
          return (
            <button
              key={game.game_id}
              onClick={() =>
                onGameSelect(isSelected ? null : game.game_id)
              }
              className={`w-full flex items-center justify-center gap-2 py-2.5 px-4 border-b border-border-default transition-colors cursor-pointer ${
                isSelected
                  ? "bg-bg-elevated border-l-2 border-l-t-green"
                  : "hover:bg-bg-elevated"
              }`}
            >
              <span className="font-code text-[13px] font-medium text-text-primary w-9 text-center">
                {game.away_abbr}
              </span>
              <span className="font-code text-[11px] text-text-muted">@</span>
              <span className="font-code text-[13px] font-medium text-text-primary w-9 text-center">
                {game.home_abbr}
              </span>
            </button>
          );
        })}
      </div>

      {games.length === 0 && (
        <p className="text-text-muted text-xs text-center mt-8 font-code">
          No games today
        </p>
      )}
    </aside>
  );
}
