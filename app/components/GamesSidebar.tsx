"use client";

import { useState } from "react";
import type { Game } from "@/app/lib/types";

interface GamesSidebarProps {
  games: Game[];
  selectedGame: string | null;
  onGameSelect: (gameId: string | null) => void;
}

export default function GamesSidebar({ games, selectedGame, onGameSelect }: GamesSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <button onClick={() => setCollapsed(false)}
        className="fixed right-0 top-16 bg-tv-bg-secondary border border-tv-border rounded-l-lg px-2 py-3 text-tv-text-secondary text-xs hover:text-tv-text z-20">
        ◀ {games.length}G
      </button>
    );
  }

  return (
    <aside className="w-48 shrink-0 bg-tv-bg-secondary border-l border-tv-border p-3 overflow-y-auto hidden lg:block">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-tv-text-secondary text-xs font-medium uppercase tracking-wider">Today&apos;s Games</h3>
        <button onClick={() => setCollapsed(true)} className="text-tv-text-secondary hover:text-tv-text text-xs">▶</button>
      </div>
      <button onClick={() => onGameSelect(null)}
        className={`w-full text-left px-2 py-1.5 rounded text-xs mb-1 transition-colors ${
          selectedGame === null ? "bg-tv-blue/20 text-tv-blue" : "text-tv-text-secondary hover:text-tv-text hover:bg-tv-bg-tertiary"
        }`}>
        All Games
      </button>
      <div className="space-y-1">
        {games.map((game) => (
          <button key={game.game_id} onClick={() => onGameSelect(selectedGame === game.game_id ? null : game.game_id)}
            className={`w-full text-left px-2 py-2 rounded text-xs transition-colors ${
              selectedGame === game.game_id
                ? "bg-tv-blue/20 border border-tv-blue/30"
                : "hover:bg-tv-bg-tertiary border border-transparent"
            }`}>
            <div className="flex items-center justify-between">
              <span className="text-tv-text font-medium">{game.away_abbr}</span>
              <span className="text-tv-text-secondary">@</span>
              <span className="text-tv-text font-medium">{game.home_abbr}</span>
            </div>
          </button>
        ))}
      </div>
      {games.length === 0 && <p className="text-tv-text-secondary text-xs text-center mt-4">No games today</p>}
    </aside>
  );
}
