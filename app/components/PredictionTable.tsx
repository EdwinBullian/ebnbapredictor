"use client";

import { useState } from "react";
import type { Prediction } from "@/app/lib/types";

interface PredictionTableProps {
  predictions: Prediction[];
  gameFilter: string | null;
}

type SortKey = "player_name" | "team" | "opponent" | "predicted" | "line" | "edge" | "confidence";

interface SortHeaderProps {
  label: string;
  sortKey: SortKey;
  activeSortKey: SortKey;
  sortAsc: boolean;
  onSort: (key: SortKey) => void;
}

function SortHeader({ label, sortKey, activeSortKey, sortAsc, onSort }: SortHeaderProps) {
  const isActive = activeSortKey === sortKey;
  return (
    <th
      className="px-3 py-2 text-left text-xs font-medium text-tv-text-secondary uppercase tracking-wider cursor-pointer hover:text-tv-text select-none"
      onClick={() => onSort(sortKey)}
    >
      <span className="flex items-center gap-1">
        {label}
        {isActive && <span className="text-tv-blue">{sortAsc ? "▲" : "▼"}</span>}
      </span>
    </th>
  );
}

function edgeColorClass(edge: number | null): string {
  if (edge === null) return "text-tv-text-secondary";
  if (edge > 0) return "text-tv-green";
  if (edge < 0) return "text-red-400";
  return "text-tv-text-secondary";
}

function confidenceBadgeClass(confidence: number | null): string {
  if (confidence === null) return "bg-tv-bg-tertiary text-tv-text-secondary";
  if (confidence >= 70) return "bg-tv-green/20 text-tv-green";
  if (confidence >= 50) return "bg-yellow-500/20 text-yellow-400";
  return "bg-tv-bg-tertiary text-tv-text-secondary";
}

export default function PredictionTable({ predictions, gameFilter }: PredictionTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("confidence");
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedPlayer, setExpandedPlayer] = useState<string | null>(null);

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
          p.opponent.toLowerCase().includes(gameFilter.toLowerCase())
      )
    : predictions;

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortKey] ?? (typeof a[sortKey] === "number" ? -Infinity : "");
    const bVal = b[sortKey] ?? (typeof b[sortKey] === "number" ? -Infinity : "");
    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortAsc ? aVal - bVal : bVal - aVal;
    }
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortAsc ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
  });

  return (
    <div className="rounded-lg border border-tv-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-tv-bg-secondary border-b border-tv-border">
            <tr>
              <SortHeader label="Player" sortKey="player_name" activeSortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
              <SortHeader label="Team" sortKey="team" activeSortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
              <SortHeader label="Opp" sortKey="opponent" activeSortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
              <SortHeader label="Pred" sortKey="predicted" activeSortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
              <SortHeader label="Line" sortKey="line" activeSortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
              <SortHeader label="Edge" sortKey="edge" activeSortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
              <SortHeader label="Conf" sortKey="confidence" activeSortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
            </tr>
          </thead>
          <tbody className="divide-y divide-tv-border">
            {sorted.map((p) => {
              const rowKey = `${p.player_name}-${p.stat_type}`;
              const isExpanded = expandedPlayer === rowKey;
              return (
                <>
                  <tr
                    key={rowKey}
                    onClick={() => setExpandedPlayer(isExpanded ? null : rowKey)}
                    className="bg-tv-bg hover:bg-tv-bg-secondary cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-2.5 text-tv-text font-medium whitespace-nowrap">{p.player_name}</td>
                    <td className="px-3 py-2.5 text-tv-text-secondary">{p.team}</td>
                    <td className="px-3 py-2.5 text-tv-text-secondary">{p.opponent}</td>
                    <td className="px-3 py-2.5 text-tv-text font-medium">{p.predicted.toFixed(1)}</td>
                    <td className="px-3 py-2.5 text-tv-text-secondary">
                      {p.line !== null ? p.line.toFixed(1) : <span className="text-tv-text-secondary/50">—</span>}
                    </td>
                    <td className={`px-3 py-2.5 font-medium ${edgeColorClass(p.edge)}`}>
                      {p.edge !== null ? (
                        <span>{p.edge > 0 ? "+" : ""}{p.edge.toFixed(1)}</span>
                      ) : (
                        <span className="text-tv-text-secondary/50">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      {p.confidence !== null ? (
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${confidenceBadgeClass(p.confidence)}`}>
                          {p.confidence}%
                        </span>
                      ) : (
                        <span className="text-tv-text-secondary/50">—</span>
                      )}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${rowKey}-expanded`} className="bg-tv-bg-secondary/50">
                      <td colSpan={7} className="px-4 py-3">
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs mb-3">
                          <div>
                            <span className="text-tv-text-secondary uppercase tracking-wider">Direction</span>
                            <p className={`font-semibold mt-0.5 ${p.direction === "OVER" ? "text-tv-green" : p.direction === "UNDER" ? "text-red-400" : "text-tv-text-secondary"}`}>
                              {p.direction ?? "—"}
                            </p>
                          </div>
                          <div>
                            <span className="text-tv-text-secondary uppercase tracking-wider">Season Avg</span>
                            <p className="text-tv-text font-semibold mt-0.5">{p.season_avg.toFixed(1)}</p>
                          </div>
                          <div>
                            <span className="text-tv-text-secondary uppercase tracking-wider">L5 Avg</span>
                            <p className="text-tv-text font-semibold mt-0.5">{p.avg_last_5.toFixed(1)}</p>
                          </div>
                          <div>
                            <span className="text-tv-text-secondary uppercase tracking-wider">Last 5 Games</span>
                            <div className="flex gap-1 mt-0.5">
                              {p.last_5_games.length > 0 ? (
                                p.last_5_games.map((val, i) => (
                                  <span key={i} className="bg-tv-bg-tertiary rounded px-1.5 py-0.5 text-tv-text text-xs">
                                    {val}
                                  </span>
                                ))
                              ) : (
                                <span className="text-tv-text-secondary">—</span>
                              )}
                            </div>
                          </div>
                        </div>
                        {p.key_factors.length > 0 && (
                          <div>
                            <span className="text-tv-text-secondary text-xs uppercase tracking-wider">Key Factors</span>
                            <ul className="mt-1 space-y-0.5">
                              {p.key_factors.map((factor, i) => (
                                <li key={i} className="text-tv-text text-xs flex items-start gap-1.5">
                                  <span className="text-tv-blue mt-0.5">•</span>
                                  {factor}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-tv-text-secondary text-sm">
                  No predictions available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
