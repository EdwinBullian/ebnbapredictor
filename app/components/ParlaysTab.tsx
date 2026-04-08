"use client";

import { Parlay, ParlayPick } from "@/app/lib/types";

interface ParlaysTabProps {
  parlays: Parlay[];
}

function PickRow({ pick }: { pick: ParlayPick }) {
  const isOver = pick.direction === "OVER";
  const directionColor = isOver ? "text-t-green" : "text-t-red";
  const edgeCol = pick.edge >= 0 ? "text-t-green" : "text-t-red";

  return (
    <div className="flex items-center gap-3 py-2 border-b border-border-default last:border-b-0">
      <span className="shrink-0 px-2 py-0.5 text-xs font-code font-semibold bg-bg-elevated text-text-primary">
        {pick.stat_abbr}
      </span>

      <div className="flex-1 min-w-0">
        <span className="text-sm font-semibold text-text-primary truncate block font-ui">
          {pick.player_name}
        </span>
        <span className="text-xs text-text-secondary font-code">
          {pick.team} vs {pick.opponent}
        </span>
      </div>

      <div className={`text-sm font-semibold ${directionColor} shrink-0 font-code`}>
        {pick.direction} {pick.line}
      </div>

      <div className={`text-xs font-code ${edgeCol} shrink-0 w-16 text-right`}>
        Edge: {pick.edge >= 0 ? "+" : ""}
        {(pick.edge * 100).toFixed(1)}%
      </div>
    </div>
  );
}

function ParlayCard({ parlay }: { parlay: Parlay }) {
  const isPowerPlay = parlay.recommended_play === "Power";
  const evPositive = parlay.expected_value >= 0;
  const evColor = evPositive ? "text-t-green" : "text-t-red";
  const recommendedBadgeClass = isPowerPlay
    ? "bg-t-green text-bg-primary text-xs font-bold px-2 py-0.5 font-code"
    : "bg-accent-blue text-white text-xs font-bold px-2 py-0.5 font-code";

  return (
    <div className="bg-bg-surface border border-border-default overflow-hidden">
      <div className="px-4 py-3 border-b border-border-default flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-text-primary truncate font-ui">
            {parlay.strategy}
          </h3>
          <span className="text-xs text-text-secondary font-code">
            {parlay.size}-leg parlay
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className={recommendedBadgeClass}>
            {parlay.recommended_play}
          </span>

          <span className="text-xs font-code text-text-primary bg-bg-elevated px-2 py-0.5">
            {isPowerPlay ? parlay.power_payout : parlay.flex_payouts[String(parlay.size)] ?? parlay.power_payout}x
          </span>

          <span className={`text-xs font-code ${evColor} bg-bg-elevated px-2 py-0.5`}>
            EV {parlay.expected_value >= 0 ? "+" : ""}
            {(parlay.expected_value * 100).toFixed(1)}%
          </span>

          <span className="text-xs font-code text-text-secondary bg-bg-elevated px-2 py-0.5">
            {(parlay.all_hit_probability * 100).toFixed(1)}% hit
          </span>
        </div>
      </div>

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
      <div className="flex items-center justify-center py-20 text-text-secondary text-sm font-code">
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
