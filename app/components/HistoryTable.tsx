"use client";

import { useState } from "react";
import type { HistoryEntry } from "@/app/lib/types";

interface HistoryTableProps {
  history: HistoryEntry[];
}

type StatFilter = "All" | "PTS" | "REB" | "AST";

const STAT_ABBR: Record<string, string> = {
  Points: "PTS",
  Rebounds: "REB",
  Assists: "AST",
};

const FILTER_MAP: Record<StatFilter, string | null> = {
  All: null,
  PTS: "Points",
  REB: "Rebounds",
  AST: "Assists",
};

export default function HistoryTable({ history }: HistoryTableProps) {
  const [filter, setFilter] = useState<StatFilter>("All");

  const filtered =
    filter === "All"
      ? history
      : history.filter((e) => e.stat_type === FILTER_MAP[filter]);

  const filters: StatFilter[] = ["All", "PTS", "REB", "AST"];

  return (
    <div className="bg-tv-bg-secondary border border-tv-border rounded-lg overflow-hidden">
      {/* Filter bar */}
      <div className="flex gap-2 p-3 border-b border-tv-border">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              filter === f
                ? "bg-tv-accent text-white"
                : "text-tv-text-muted hover:text-tv-text hover:bg-tv-bg"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="py-12 text-center text-tv-text-muted text-sm">
          No history entries found.
        </div>
      ) : (
        <div className="overflow-y-auto max-h-96">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-tv-bg-secondary border-b border-tv-border">
              <tr>
                {["Date", "Player", "Stat", "Pred", "Line", "Dir", "Actual", "Result"].map(
                  (h) => (
                    <th
                      key={h}
                      className="text-left text-tv-text-muted text-xs uppercase px-3 py-2 font-medium"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry) => {
                const isPending = entry.actual === null;
                const isWin = entry.correct === 1;
                const isLoss = entry.correct === 0;

                const resultCell = isPending ? (
                  <span className="text-yellow-400">...</span>
                ) : isWin ? (
                  <span className="text-green-400 font-semibold">W</span>
                ) : (
                  <span className="text-red-400 font-semibold">L</span>
                );

                const dirColor =
                  entry.direction === "OVER"
                    ? "text-green-400"
                    : entry.direction === "UNDER"
                    ? "text-red-400"
                    : "text-tv-text-muted";

                return (
                  <tr
                    key={entry.id}
                    className="border-b border-tv-border last:border-0 hover:bg-tv-bg transition-colors"
                  >
                    <td className="px-3 py-2 text-tv-text-muted whitespace-nowrap">
                      {entry.date}
                    </td>
                    <td className="px-3 py-2 text-tv-text font-medium whitespace-nowrap">
                      {entry.player_name}
                    </td>
                    <td className="px-3 py-2 text-tv-text-muted">
                      {STAT_ABBR[entry.stat_type] ?? entry.stat_type}
                    </td>
                    <td className="px-3 py-2 text-tv-text">{entry.predicted}</td>
                    <td className="px-3 py-2 text-tv-text">{entry.line}</td>
                    <td className={`px-3 py-2 font-medium ${dirColor}`}>
                      {entry.direction}
                    </td>
                    <td className="px-3 py-2 text-tv-text">
                      {entry.actual !== null ? entry.actual : (
                        <span className="text-yellow-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2">{resultCell}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
