"use client";

import { useEffect, useState } from "react";
import type { Prediction, RecordResponse, HistoryEntry } from "@/app/lib/types";
import { fetchRecord, fetchHistory, lockPredictions, updateResults } from "@/app/lib/api";
import RecordSummary from "./RecordSummary";
import EquityCurve from "./EquityCurve";
import HistoryTable from "./HistoryTable";

interface RecordTabProps {
  allPredictions: Prediction[];
}

export default function RecordTab({ allPredictions }: RecordTabProps) {
  const [record, setRecord] = useState<RecordResponse | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [actionError, setActionError] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [rec, hist] = await Promise.all([
          fetchRecord(),
          fetchHistory(200),
        ]);
        setRecord(rec);
        setHistory(hist.history);
      } catch (err) {
        console.error("Failed to load record/history:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleLock() {
    setActionMsg(null);
    setActionError(false);
    try {
      const res = await lockPredictions(allPredictions);
      setActionMsg(res.message ?? `Locked ${res.saved} predictions.`);
    } catch (err) {
      setActionMsg(err instanceof Error ? err.message : "Failed to lock predictions.");
      setActionError(true);
    }
  }

  async function handleUpdate() {
    setActionMsg(null);
    setActionError(false);
    try {
      const res = await updateResults();
      setActionMsg(res.message ?? `Updated ${res.updated} results.`);
      const [rec, hist] = await Promise.all([fetchRecord(), fetchHistory(200)]);
      setRecord(rec);
      setHistory(hist.history);
    } catch (err) {
      setActionMsg(err instanceof Error ? err.message : "Failed to update results.");
      setActionError(true);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="bg-bg-surface border border-border-default p-4 h-24"
            />
          ))}
        </div>
        <div className="bg-bg-surface border border-border-default h-52" />
        <div className="bg-bg-surface border border-border-default h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <button
          onClick={handleLock}
          className="px-4 py-2 bg-t-green text-bg-primary text-sm font-code font-bold hover:opacity-90 transition-opacity cursor-pointer"
        >
          Lock Predictions
        </button>
        <button
          onClick={handleUpdate}
          className="px-4 py-2 bg-bg-surface border border-border-default text-text-primary text-sm font-code font-medium hover:bg-bg-elevated transition-colors cursor-pointer"
        >
          Update Results
        </button>
        {actionMsg && (
          <p
            className={`text-sm font-code ${
              actionError ? "text-t-red" : "text-t-green"
            }`}
          >
            {actionMsg}
          </p>
        )}
      </div>

      {record && <RecordSummary record={record} />}

      {record && record.recent_days.length >= 2 && (
        <EquityCurve recentDays={record.recent_days} />
      )}

      <HistoryTable history={history} />
    </div>
  );
}
