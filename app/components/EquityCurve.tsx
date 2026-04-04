"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { DayRecord } from "@/app/lib/types";

interface EquityCurveProps {
  recentDays: DayRecord[];
}

interface ChartPoint {
  date: string;
  winPct: number;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${mm}-${dd}`;
}

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}) => {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-tv-bg-secondary border border-tv-border rounded px-3 py-2 text-sm">
      <p className="text-tv-text-muted">{label}</p>
      <p className="text-green-400 font-semibold">
        {payload[0].value.toFixed(1)}%
      </p>
    </div>
  );
};

export default function EquityCurve({ recentDays }: EquityCurveProps) {
  if (recentDays.length < 2) return null;

  // Reverse to chronological order
  const chronological = [...recentDays].reverse();

  // Accumulate wins/total for cumulative win%
  let cumWins = 0;
  let cumTotal = 0;
  const data: ChartPoint[] = chronological.map((day) => {
    cumWins += day.wins;
    cumTotal += day.total;
    return {
      date: formatDate(day.date),
      winPct: cumTotal > 0 ? (cumWins / cumTotal) * 100 : 0,
    };
  });

  return (
    <div className="bg-tv-bg-secondary border border-tv-border rounded-lg p-4">
      <p className="text-tv-text-muted text-xs uppercase tracking-wide mb-4">
        Cumulative Hit Rate
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
          <XAxis
            dataKey="date"
            tick={{ fill: "#888", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: "#888", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={42}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={50}
            stroke="#555"
            strokeDasharray="4 4"
            label={{ value: "50%", fill: "#888", fontSize: 11 }}
          />
          <Line
            type="monotone"
            dataKey="winPct"
            stroke="#26a69a"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#26a69a" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
