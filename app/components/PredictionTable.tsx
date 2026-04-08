"use client";

import { useState, Fragment } from "react";
import type { Prediction } from "@/app/lib/types";

interface PredictionTableProps {
  predictions: Prediction[];
  gameFilter: string | null;
}

type SortKey =
  | "player_name"
  | "team"
  | "opponent"
  | "predicted"
  | "line"
  | "edge"
  | "confidence";

function SortHeader({
  label,
  sortKey,
  activeSortKey,
  sortAsc,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  activeSortKey: SortKey;
  sortAsc: boolean;
  onSort: (key: SortKey) => void;
}) {
  const isActive = activeSortKey === sortKey;
  return (
    <th
      className="px-3 py-2.5 text-left font-code text-[11px] font-medium text-text-secondary uppercase tracking-[0.05em] cursor-pointer hover:text-text-primary select-none bg-bg-header"
      onClick={() => onSort(sortKey)}
    >
      <span className="flex items-center gap-1">
        {label}
        {isActive && (
          <span className="text-t-green">{sortAsc ? "\u25B2" : "\u25BC"}</span>
        )}
      </span>
    </th>
  );
}

function edgeColor(edge: number | null): string {
  if (edge === null) return "text-text-muted";
  if (edge > 0) return "text-t-green";
  if (edge < 0) return "text-t-red";
  return "text-text-secondary";
}

function confPill(conf: number | null): string {
  if (conf === null) return "bg-bg-elevated text-text-muted border-border-default";
  if (conf >= 50)
    return "bg-t-green-bar text-t-green border-t-green/30";
  if (conf >= 40)
    return "bg-[rgba(245,158,11,0.2)] text-accent-amber border-accent-amber/30";
  return "bg-[rgba(136,136,136,0.15)] text-text-secondary border-border-default";
}

/* ── Expanded detail panel with bar chart ── */
function ExpandedPanel({ p }: { p: Prediction }) {
  const games = p.last_5_games;
  const line = p.line;
  const maxVal = Math.max(...games, line ?? 0, 1);

  return (
    <div className="bg-bg-elevated border-l-[3px] border-l-t-green flex gap-6 p-4">
      {/* Bar chart */}
      <div className="flex-1 min-w-[240px]">
        <div className="font-code text-[11px] font-medium uppercase tracking-[0.05em] text-text-secondary mb-2.5">
          Last {games.length} Games &mdash;{" "}
          {p.stat_type === "Points"
            ? "Points"
            : p.stat_type === "Rebounds"
              ? "Rebounds"
              : "Assists"}
        </div>
        {games.length > 0 ? (
          <div className="relative h-[120px] flex items-end gap-2 px-1">
            {/* Reference line */}
            {line !== null && (
              <div
                className="absolute left-0 right-0 border-t border-dashed border-text-muted z-[1]"
                style={{ bottom: `${(line / maxVal) * 100}%` }}
              >
                <span className="absolute right-0 font-code text-[10px] text-text-muted -translate-y-3">
                  LINE {line}
                </span>
              </div>
            )}
            {games.map((val, i) => {
              const isOver = line !== null && val > line;
              const h = (val / maxVal) * 100;
              return (
                <div key={i} className="flex-1 flex flex-col items-center">
                  <div className="w-full relative" style={{ height: "100px" }}>
                    <div
                      className={`absolute bottom-0 w-full ${
                        isOver ? "bg-t-green" : "bg-t-red"
                      }`}
                      style={{
                        height: `${h}%`,
                        boxShadow: isOver
                          ? "0 0 8px rgba(0,255,102,0.3)"
                          : "0 0 8px rgba(255,59,59,0.3)",
                      }}
                    />
                  </div>
                  <span className="font-code text-[10px] font-semibold text-text-secondary mt-1">
                    {val}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="h-[120px] flex items-center justify-center text-text-muted font-code text-xs">
            No game data
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="w-[200px] flex flex-col gap-2">
        {[
          { label: "Season Avg", value: p.season_avg.toFixed(1) },
          {
            label: "Last 5 Avg",
            value: p.avg_last_5.toFixed(1),
            color:
              p.avg_last_5 > p.season_avg ? "text-t-green" : "text-t-red",
          },
          {
            label: "Predicted",
            value: p.predicted.toFixed(1),
            color:
              p.line !== null && p.predicted > p.line
                ? "text-t-green"
                : p.line !== null
                  ? "text-t-red"
                  : undefined,
          },
          {
            label: "Line",
            value: p.line !== null ? p.line.toFixed(1) : "\u2014",
          },
        ].map((s) => (
          <div
            key={s.label}
            className="flex justify-between items-center py-1 border-b border-border-default"
          >
            <span className="font-code text-[11px] text-text-secondary uppercase tracking-[0.05em]">
              {s.label}
            </span>
            <span
              className={`font-code text-[13px] font-semibold ${s.color ?? "text-text-primary"}`}
            >
              {s.value}
            </span>
          </div>
        ))}

        {p.key_factors.length > 0 && (
          <div className="mt-1">
            <span className="font-code text-[11px] text-text-secondary uppercase tracking-[0.05em]">
              Key Factors
            </span>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {p.key_factors.map((f, i) => (
                <span
                  key={i}
                  className="font-code text-[10px] px-1.5 py-0.5 bg-bg-surface border border-border-default text-text-secondary"
                >
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PredictionTable({
  predictions,
  gameFilter,
}: PredictionTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("confidence");
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedPlayer, setExpandedPlayer] = useState<string | null>(null);
  const [showNoLines, setShowNoLines] = useState(false);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((prev) => !prev);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const filtered = gameFilter
    ? predictions.filter(
        (p) =>
          p.team.toLowerCase().includes(gameFilter.toLowerCase()) ||
          p.opponent.toLowerCase().includes(gameFilter.toLowerCase()),
      )
    : predictions;

  // Separate players with lines from those without
  const withLines = filtered.filter((p) => p.line !== null);
  const noLines = filtered.filter((p) => p.line === null);

  const sorted = [...withLines].sort((a, b) => {
    const aVal =
      a[sortKey] ?? (typeof a[sortKey] === "number" ? -Infinity : "");
    const bVal =
      b[sortKey] ?? (typeof b[sortKey] === "number" ? -Infinity : "");
    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortAsc ? aVal - bVal : bVal - aVal;
    }
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortAsc ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
  });

  const renderRow = (p: Prediction) => {
    const rowKey = `${p.player_name}-${p.stat_type}`;
    const isExpanded = expandedPlayer === rowKey;

    return (
      <Fragment key={rowKey}>
        <tr
          onClick={() => setExpandedPlayer(isExpanded ? null : rowKey)}
          className="border-b border-border-default hover:bg-bg-elevated cursor-pointer transition-colors"
        >
          <td className="px-3 py-2.5 font-ui text-sm font-medium text-text-primary whitespace-nowrap">
            {p.player_name}
          </td>
          <td className="px-3 py-2.5 font-code text-xs text-text-secondary">
            {p.team}
          </td>
          <td className="px-3 py-2.5 font-code text-xs text-text-secondary">
            {p.opponent}
          </td>
          <td className="px-3 py-2.5 font-code text-sm font-semibold text-text-primary">
            {p.predicted.toFixed(1)}
          </td>
          <td className="px-3 py-2.5 font-code text-sm text-text-secondary">
            {p.line !== null ? (
              p.line.toFixed(1)
            ) : (
              <span className="text-text-muted">&mdash;</span>
            )}
          </td>
          <td
            className={`px-3 py-2.5 font-code text-sm font-bold ${edgeColor(p.edge)}`}
          >
            {p.edge !== null ? (
              `${p.edge > 0 ? "+" : ""}${p.edge.toFixed(1)}`
            ) : (
              <span className="text-text-muted">&mdash;</span>
            )}
          </td>
          <td className="px-3 py-2.5">
            {p.confidence !== null ? (
              <span
                className={`inline-flex items-center justify-center min-w-[44px] px-2 py-0.5 font-code text-[11px] font-bold border ${confPill(p.confidence)}`}
              >
                {p.confidence}%
              </span>
            ) : (
              <span className="text-text-muted font-code text-sm">
                &mdash;
              </span>
            )}
          </td>
        </tr>
        {isExpanded && (
          <tr>
            <td colSpan={7} className="p-0">
              <ExpandedPanel p={p} />
            </td>
          </tr>
        )}
      </Fragment>
    );
  };

  return (
    <div className="border border-border-default overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-bright">
              <SortHeader
                label="Player"
                sortKey="player_name"
                activeSortKey={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortHeader
                label="Team"
                sortKey="team"
                activeSortKey={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortHeader
                label="Opp"
                sortKey="opponent"
                activeSortKey={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortHeader
                label="Pred"
                sortKey="predicted"
                activeSortKey={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortHeader
                label="Line"
                sortKey="line"
                activeSortKey={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortHeader
                label="Edge"
                sortKey="edge"
                activeSortKey={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
              <SortHeader
                label="Conf"
                sortKey="confidence"
                activeSortKey={sortKey}
                sortAsc={sortAsc}
                onSort={handleSort}
              />
            </tr>
          </thead>
          <tbody className="bg-bg-surface">
            {sorted.map(renderRow)}
            {sorted.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-3 py-8 text-center text-text-muted text-sm font-code"
                >
                  No predictions available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* No Lines section */}
      {noLines.length > 0 && (
        <div className="border-t border-border-default">
          <button
            onClick={() => setShowNoLines(!showNoLines)}
            className="w-full flex items-center gap-2 px-3 py-2 font-code text-[10px] tracking-[0.08em] uppercase text-text-muted hover:text-text-secondary cursor-pointer"
          >
            <span>{showNoLines ? "\u25BC" : "\u25B6"}</span>
            No Lines Available
            <span className="text-[10px] bg-bg-elevated px-1.5 py-0.5">
              {noLines.length}
            </span>
          </button>
          {showNoLines && (
            <table className="w-full text-sm">
              <tbody className="bg-bg-surface">
                {noLines.map(renderRow)}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
