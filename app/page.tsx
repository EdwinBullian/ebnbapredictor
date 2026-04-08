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
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    const load = () => {
      fetchPredictions()
        .then((res) => {
          if (cancelled) return;
          setData(res);
          setLoading(false);
          if (res.loading) {
            pollTimer = setTimeout(load, 15_000);
          }
        })
        .catch((err: Error) => {
          if (cancelled) return;
          setError(err.message);
          setLoading(false);
        });
    };

    load();
    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, []);

  function getCurrentPredictions(): Prediction[] {
    if (!data) return [];
    if (activeTab === "rebounds") return data.rebounds;
    if (activeTab === "assists") return data.assists;
    return data.points;
  }

  const allPredictions: Prediction[] = data
    ? [...data.points, ...data.rebounds, ...data.assists]
    : [];

  function getGameFilter(): string | null {
    if (!selectedGame || !data) return null;
    const game: Game | undefined = data.games.find((g) => g.game_id === selectedGame);
    return game ? game.home_abbr : null;
  }

  const currentPredictions = getCurrentPredictions();
  const gameFilter = getGameFilter();
  const isStatTab = activeTab !== "parlays" && activeTab !== "record";

  return (
    <div className="min-h-screen flex flex-col bg-bg-primary">
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="mb-4 bg-t-red-dim border border-t-red/30 px-4 py-3 text-t-red text-sm font-code">
              {error}
            </div>
          )}

          {loading ? (
            <SkeletonLoader />
          ) : data?.loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-text-secondary">
              <div className="animate-spin h-10 w-10 border-2 border-text-secondary border-t-t-green mb-4" />
              <p className="text-sm font-code">Generating today&apos;s predictions&hellip;</p>
              <p className="text-xs mt-1 text-text-muted font-code">This takes ~2 minutes on first load. Auto-refreshing.</p>
            </div>
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
            <p className="mt-4 text-text-muted text-xs text-center font-code">{data.message}</p>
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
