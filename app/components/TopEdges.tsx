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
    <div className="bg-bg-surface border border-t-green/15 mb-4">
      <div className="px-3 pt-2.5 pb-1.5">
        <span
          className="font-code text-[10px] font-semibold tracking-[0.12em] uppercase text-t-green"
          style={{ textShadow: "0 0 8px rgba(0,255,102,0.2)" }}
        >
          TOP EDGES
        </span>
      </div>
      <div className="flex hide-scrollbar overflow-x-auto">
        {topEdges.map((p, i) => (
          <div
            key={`${p.player_name}-${p.stat_type}`}
            className={`flex items-center gap-1.5 px-3 py-2 font-code text-[11px] whitespace-nowrap shrink-0 ${
              i < topEdges.length - 1 ? "border-r border-border-default" : ""
            } ${p.direction === "OVER" ? "bg-t-green-dim" : "bg-t-red-dim"}`}
          >
            <span className="text-text-primary font-medium">
              {p.player_name}
            </span>
            <span
              className={`font-bold ${
                p.direction === "OVER" ? "text-t-green" : "text-t-red"
              }`}
            >
              {p.direction}
            </span>
            <span className="text-text-secondary">{p.line}</span>
            <span
              className={`font-bold ${
                p.direction === "OVER" ? "text-t-green" : "text-t-red"
              }`}
            >
              (+{p.edge?.toFixed(1)})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
