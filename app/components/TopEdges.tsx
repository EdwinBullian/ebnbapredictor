import type { Prediction } from "@/app/lib/types";

interface TopEdgesProps {
  predictions: Prediction[];
}

export default function TopEdges({ predictions }: TopEdgesProps) {
  const topEdges = predictions
    .filter((p) => p.edge !== null && p.edge > 0 && p.line !== null)
    .sort((a, b) => (b.edge ?? 0) - (a.edge ?? 0))
    .slice(0, 5);

  if (topEdges.length === 0) return null;

  return (
    <div className="bg-tv-green-bg border border-tv-green/20 rounded-lg px-4 py-3 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-tv-green text-xs font-semibold uppercase tracking-wider">Top Edges</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {topEdges.map((p) => (
          <span key={`${p.player_name}-${p.stat_type}`} className="bg-tv-bg/60 rounded px-3 py-1 text-xs">
            <span className="text-tv-text font-medium">{p.player_name}</span>{" "}
            <span className="text-tv-green">{p.direction} {p.line} (+{p.edge?.toFixed(1)})</span>
          </span>
        ))}
      </div>
    </div>
  );
}
