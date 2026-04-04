"use client";

import { useEffect, useState } from "react";
import { fetchPredictions } from "@/app/lib/api";
import type { PredictionsResponse, TabType, Game, Prediction } from "@/app/lib/types";
import Navbar from "@/app/components/Navbar";
import GamesSidebar from "@/app/components/GamesSidebar";
import TopEdges from "@/app/components/TopEdges";
import PredictionTable from "@/app/components/PredictionTable";
import ParlaysTab from "@/app/components/ParlaysTab";
import RecordTab from "@/app/components/RecordTab";
import SkeletonLoader from "@/app/components/SkeletonLoader";

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
