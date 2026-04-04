import type { RecordResponse } from "@/app/lib/types";

interface RecordSummaryProps {
  record: RecordResponse;
}

function winPctColor(pct: number): string {
  if (pct >= 0.55) return "text-green-400";
  if (pct >= 0.5) return "text-yellow-400";
  return "text-red-400";
}

function StatCard({
  label,
  wins,
  losses,
  winPct,
}: {
  label: string;
  wins: number;
  losses: number;
  winPct: number;
}) {
  const color = winPctColor(winPct);
  return (
    <div className="bg-tv-bg-secondary border border-tv-border rounded-lg p-4">
      <p className="text-tv-text-muted text-xs uppercase tracking-wide mb-2">
        {label}
      </p>
      <p className="text-tv-text text-lg font-semibold">
        {wins}-{losses}
      </p>
      <p className={`text-sm font-medium ${color}`}>
        {(winPct * 100).toFixed(1)}%
      </p>
    </div>
  );
}

export default function RecordSummary({ record }: RecordSummaryProps) {
  const { overall, by_stat } = record;

  const statLabels: Record<string, string> = {
    Points: "Points",
    Rebounds: "Rebounds",
    Assists: "Assists",
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Overall"
          wins={overall.wins}
          losses={overall.losses}
          winPct={overall.win_pct}
        />
        {by_stat
          .filter((s) => s.stat_type in statLabels)
          .map((s) => (
            <StatCard
              key={s.stat_type}
              label={statLabels[s.stat_type] ?? s.stat_type}
              wins={s.wins}
              losses={s.total - s.wins}
              winPct={s.win_pct}
            />
          ))}
        {overall.pending > 0 && (
          <div className="bg-tv-bg-secondary border border-tv-border rounded-lg p-4">
            <p className="text-tv-text-muted text-xs uppercase tracking-wide mb-2">
              Pending
            </p>
            <p className="text-yellow-400 text-lg font-semibold">
              {overall.pending}
            </p>
            <p className="text-tv-text-muted text-sm">awaiting results</p>
          </div>
        )}
      </div>
    </div>
  );
}
