"use client";

import { useEffect, useState } from "react";
import { fetchPredictions } from "@/app/lib/api";
import type { PredictionsResponse, TabType, Game, Prediction, Parlay } from "@/app/lib/types";
import Navbar from "@/app/components/Navbar";
import GamesSidebar from "@/app/components/GamesSidebar";
import TopEdges from "@/app/components/TopEdges";
import PredictionTable from "@/app/components/PredictionTable";
import RecordSummary from "@/app/components/RecordSummary";
import SkeletonLoader from "@/app/components/SkeletonLoader";

// ── Inline Parlays Tab ────────────────────────────────────────────────────────

function ParlayCard({ parlay }: { parlay: Parlay }) {
  return (
    <div className="bg-tv-bg-secondary border border-tv-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-tv-text font-semibold text-sm">{parlay.strategy}</span>
        <span className="text-xs bg-tv-blue/20 text-tv-blue px-2 py-0.5 rounded font-medium">
          {parlay.size}-pick
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <p className="text-tv-text-secondary uppercase tracking-wider mb-0.5">Hit Prob</p>
          <p className="text-tv-text font-semibold">{(parlay.all_hit_probability * 100).toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-tv-text-secondary uppercase tracking-wider mb-0.5">Power Pay</p>
          <p className="text-tv-green font-semibold">{parlay.power_payout}</p>
        </div>
        <div>
          <p className="text-tv-text-secondary uppercase tracking-wider mb-0.5">Power EV</p>
          <p className={`font-semibold ${parlay.power_ev > 0 ? "text-tv-green" : "text-red-400"}`}>
            {parlay.power_ev > 0 ? "+" : ""}{parlay.power_ev.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-tv-text-secondary uppercase tracking-wider mb-0.5">Rec. Play</p>
          <p className="text-tv-text font-semibold">{parlay.recommended_play}</p>
        </div>
      </div>

      <div className="border-t border-tv-border pt-2 space-y-1">
        {parlay.picks.map((pick, i) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <span className="text-tv-text font-medium">{pick.player_name}</span>
            <span className="text-tv-text-secondary">{pick.team} vs {pick.opponent}</span>
            <span className={`font-medium ${pick.direction === "OVER" ? "text-tv-green" : "text-red-400"}`}>
              {pick.direction} {pick.line} {pick.stat_abbr}
            </span>
            <span className="text-tv-text-secondary">{pick.confidence}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ParlaysTab({ parlays }: { parlays: Parlay[] }) {
  if (parlays.length === 0) {
    return (
      <div className="text-center py-12 text-tv-text-secondary text-sm">
        No parlays generated for today.
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <h2 className="text-tv-text font-semibold text-sm uppercase tracking-wider">
        Today&apos;s Parlays
      </h2>
      {parlays.map((parlay, i) => (
        <ParlayCard key={i} parlay={parlay} />
      ))}
    </div>
  );
}

// ── Inline Record Tab ─────────────────────────────────────────────────────────

function RecordTab({ allPredictions }: { allPredictions: Prediction[] }) {
  const bettable = allPredictions.filter((p) => p.bettable);
  return (
    <div className="space-y-4">
      <h2 className="text-tv-text font-semibold text-sm uppercase tracking-wider">
        Prediction Record
      </h2>
      <div className="bg-tv-bg-secondary border border-tv-border rounded-lg p-4 text-tv-text-secondary text-sm">
        <p>{allPredictions.length} total predictions loaded &mdash; {bettable.length} bettable.</p>
        <p className="mt-1 text-xs">Historical record tracking is available via the /api/record endpoint.</p>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>("points");
  const [data, setData] = useState<PredictionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<string | null>(null);

  useEffect(() => {
    fetchPredictions()
      .then((res) => setData(res))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Derive current stat predictions based on active tab
  function getCurrentPredictions(): Prediction[] {
    if (!data) return [];
    if (activeTab === "rebounds") return data.rebounds;
    if (activeTab === "assists") return data.assists;
    return data.points;
  }

  // Combine all predictions for record tab
  const allPredictions: Prediction[] = data
    ? [...data.points, ...data.rebounds, ...data.assists]
    : [];

  // Resolve game filter string from selectedGame id
  function getGameFilter(): string | null {
    if (!selectedGame || !data) return null;
    const game: Game | undefined = data.games.find((g) => g.game_id === selectedGame);
    return game ? game.home_abbr : null;
  }

  const currentPredictions = getCurrentPredictions();
  const gameFilter = getGameFilter();
  const isStatTab = activeTab !== "parlays" && activeTab !== "record";

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="mb-4 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <SkeletonLoader />
          ) : activeTab === "parlays" ? (
            <ParlaysTab parlays={data?.parlays ?? []} />
          ) : activeTab === "record" ? (
            <RecordTab allPredictions={allPredictions} />
          ) : (
            <>
              <TopEdges predictions={currentPredictions} />
              <PredictionTable predictions={currentPredictions} gameFilter={gameFilter} />
            </>
          )}

          {data?.message && (
            <p className="mt-4 text-tv-text-secondary text-xs text-center">{data.message}</p>
          )}
        </main>

        {isStatTab && (
          <GamesSidebar
            games={data?.games ?? []}
            selectedGame={selectedGame}
            onGameSelect={setSelectedGame}
          />
        )}
      </div>
    </div>
  );
}
