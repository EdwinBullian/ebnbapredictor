import type { RecordResponse } from "@/app/lib/types";

interface RecordSummaryProps {
  record: RecordResponse;
}

function winPctColor(pct: number): string {
  if (pct >= 0.55) return "text-t-green";
  if (pct >= 0.5) return "text-accent-amber";
  return "text-t-red";
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
    <div className="bg-bg-surface border border-border-default p-4">
      <p className="text-text-muted text-[10px] font-code uppercase tracking-[0.08em] mb-2">
        {label}
      </p>
      <p className="text-text-primary text-lg font-code font-semibold">
        {wins}-{losses}
      </p>
      <p className={`text-sm font-code font-medium ${color}`}>
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
          winPct={overall.win_pct ?? 0}
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
          <div className="bg-bg-surface border border-border-default p-4">
            <p className="text-text-muted text-[10px] font-code uppercase tracking-[0.08em] mb-2">
              Pending
            </p>
            <p className="text-accent-amber text-lg font-code font-semibold">
              {overall.pending}
            </p>
            <p className="text-text-muted text-sm font-code">awaiting results</p>
          </div>
        )}
      </div>
    </div>
  );
}
