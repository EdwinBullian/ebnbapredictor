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
    <div className="bg-bg-surface border border-border-default overflow-hidden">
      {/* Filter bar */}
      <div className="flex gap-2 p-3 border-b border-border-default">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 text-xs font-code font-semibold uppercase tracking-[0.05em] transition-colors cursor-pointer ${
              filter === f
                ? "bg-t-green text-bg-primary"
                : "text-text-muted hover:text-text-primary hover:bg-bg-elevated"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="py-12 text-center text-text-muted text-sm font-code">
          No history entries found.
        </div>
      ) : (
        <div className="overflow-y-auto max-h-96">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-bg-header border-b border-border-bright">
              <tr>
                {["Date", "Player", "Stat", "Pred", "Line", "Dir", "Actual", "Result"].map(
                  (h) => (
                    <th
                      key={h}
                      className="text-left text-text-secondary text-[11px] font-code uppercase tracking-[0.05em] px-3 py-2.5 font-medium"
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

                const resultCell = isPending ? (
                  <span className="text-accent-amber font-code">...</span>
                ) : isWin ? (
                  <span className="text-t-green font-code font-semibold">W</span>
                ) : (
                  <span className="text-t-red font-code font-semibold">L</span>
                );

                const dirColor =
                  entry.direction === "OVER"
                    ? "text-t-green"
                    : entry.direction === "UNDER"
                    ? "text-t-red"
                    : "text-text-muted";

                return (
                  <tr
                    key={entry.id}
                    className="border-b border-border-default last:border-0 hover:bg-bg-elevated transition-colors"
                  >
                    <td className="px-3 py-2 text-text-muted font-code text-xs whitespace-nowrap">
                      {entry.date}
                    </td>
                    <td className="px-3 py-2 text-text-primary font-ui font-medium whitespace-nowrap">
                      {entry.player_name}
                    </td>
                    <td className="px-3 py-2 text-text-secondary font-code text-xs">
                      {STAT_ABBR[entry.stat_type] ?? entry.stat_type}
                    </td>
                    <td className="px-3 py-2 text-text-primary font-code">{entry.predicted}</td>
                    <td className="px-3 py-2 text-text-primary font-code">{entry.line}</td>
                    <td className={`px-3 py-2 font-code font-medium ${dirColor}`}>
                      {entry.direction}
                    </td>
                    <td className="px-3 py-2 text-text-primary font-code">
                      {entry.actual !== null ? entry.actual : (
                        <span className="text-accent-amber">&mdash;</span>
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
