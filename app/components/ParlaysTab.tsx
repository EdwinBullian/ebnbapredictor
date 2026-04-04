"use client";

import { Parlay, ParlayPick } from "@/app/lib/types";

interface ParlaysTabProps {
  parlays: Parlay[];
}

function PickRow({ pick }: { pick: ParlayPick }) {
  const isOver = pick.direction === "OVER";
  const directionColor = isOver ? "text-tv-green" : "text-tv-red";
  const edgeColor = pick.edge >= 0 ? "text-tv-green" : "text-tv-red";

  return (
    <div className="flex items-center gap-3 py-2 border-b border-tv-border last:border-b-0">
      {/* Stat badge */}
      <span
        className="shrink-0 px-2 py-0.5 rounded text-xs font-mono font-semibold bg-tv-bg-tertiary text-tv-text"
      >
        {pick.stat_abbr}
      </span>

      {/* Player + team */}
      <div className="flex-1 min-w-0">
        <span className="text-sm font-semibold text-tv-text truncate block">
          {pick.player_name}
        </span>
        <span className="text-xs text-tv-text-secondary">
          {pick.team} vs {pick.opponent}
        </span>
      </div>

      {/* Direction + line */}
      <div className={`text-sm font-semibold ${directionColor} shrink-0`}>
        {pick.direction} {pick.line}
      </div>

      {/* Edge */}
      <div className={`text-xs font-mono ${edgeColor} shrink-0 w-16 text-right`}>
        Edge: {pick.edge >= 0 ? "+" : ""}
        {(pick.edge * 100).toFixed(1)}%
      </div>
    </div>
  );
}

function ParlayCard({ parlay }: { parlay: Parlay }) {
  const isPowerPlay = parlay.recommended_play === "Power";
  const evPositive = parlay.expected_value >= 0;
  const evColor = evPositive ? "text-tv-green" : "text-tv-red";
  const recommendedBadgeClass = isPowerPlay
    ? "bg-tv-green text-tv-bg text-xs font-bold px-2 py-0.5 rounded"
    : "bg-tv-blue text-white text-xs font-bold px-2 py-0.5 rounded";

  return (
    <div className="bg-tv-bg-secondary border border-tv-border rounded-lg overflow-hidden">
      {/* Card header */}
      <div className="px-4 py-3 border-b border-tv-border flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-tv-text truncate">
            {parlay.strategy}
          </h3>
          <span className="text-xs text-tv-text-secondary">
            {parlay.size}-leg parlay
          </span>
        </div>

        {/* Badges row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={recommendedBadgeClass}>
            {parlay.recommended_play}
          </span>

          <span className="text-xs font-mono text-tv-text bg-tv-bg-tertiary px-2 py-0.5 rounded">
            {isPowerPlay ? parlay.power_payout : parlay.flex_payouts[String(parlay.size)] ?? parlay.power_payout}x
          </span>

          <span className={`text-xs font-mono ${evColor} bg-tv-bg-tertiary px-2 py-0.5 rounded`}>
            EV {parlay.expected_value >= 0 ? "+" : ""}
            {(parlay.expected_value * 100).toFixed(1)}%
          </span>

          <span className="text-xs font-mono text-tv-text-secondary bg-tv-bg-tertiary px-2 py-0.5 rounded">
            {(parlay.all_hit_probability * 100).toFixed(1)}% hit
          </span>
        </div>
      </div>

      {/* Picks list */}
      <div className="px-4 py-1">
        {parlay.picks.map((pick, i) => (
          <PickRow key={`${pick.player_name}-${pick.stat_type}-${i}`} pick={pick} />
        ))}
      </div>
    </div>
  );
}

export default function ParlaysTab({ parlays }: ParlaysTabProps) {
  if (!parlays || parlays.length === 0) {
    return (
      <div className="flex items-center justify-center py-20 text-tv-text-secondary text-sm">
        No parlays generated yet.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {parlays.map((parlay, i) => (
        <ParlayCard key={`${parlay.strategy}-${i}`} parlay={parlay} />
      ))}
    </div>
  );
}
