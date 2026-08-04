"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from "recharts";
import { SpreadPoint, SpreadMetrics } from "@/lib/correlationTypes";

interface SpreadHistogramProps {
  data: SpreadPoint[];
  metrics: SpreadMetrics;
}

function buildBins(
  values: number[],
  binCount: number
): { min: number; max: number; mid: number; count: number }[] {
  if (values.length === 0) return [];
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const step = (hi - lo) / binCount || 1;
  const bins = Array.from({ length: binCount }, (_, i) => ({
    min: lo + i * step,
    max: lo + (i + 1) * step,
    mid: lo + (i + 0.5) * step,
    count: 0,
  }));
  for (const v of values) {
    const idx = Math.min(Math.floor((v - lo) / step), binCount - 1);
    bins[idx].count++;
  }
  return bins;
}

const TOOLTIP_STYLE = {
  backgroundColor: "rgba(0,0,0,0.85)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "12px",
  backdropFilter: "blur(12px)",
  fontSize: 12,
  color: "#e5e5e5",
};

const TOOLTIP_LABEL_STYLE = {
  color: "#f5f5f5",
  fontWeight: 600,
  marginBottom: 4,
};

const TOOLTIP_ITEM_STYLE = {
  color: "#d4d4d4",
};

const AXIS_TICK = { fill: "#737373", fontSize: 10 };
const AXIS_LINE = { stroke: "rgba(255,255,255,0.06)" };
const GRID = "rgba(255,255,255,0.04)";

export default function SpreadHistogram({ data, metrics }: SpreadHistogramProps) {
  const spreads = data.map((d) => d.spread).filter((v): v is number => v != null);
  const zscores = data.map((d) => d.zscore).filter((v): v is number => v != null);

  const spreadBins = buildBins(spreads, 40);
  const zscoreBins = buildBins(zscores, 40);

  const spreadMean = metrics.mean;
  const spreadMedian = [...spreads].sort((a, b) => a - b)[Math.floor(spreads.length / 2)] ?? 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Spread Distribution */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-neutral-300 mb-1">
          Spread Distribution
        </h3>
        <p className="text-xs text-neutral-500 mb-4">
          Histogram of spread values with mean and median
        </p>
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={spreadBins} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis
                dataKey="mid"
                tick={AXIS_TICK}
                axisLine={AXIS_LINE}
                tickLine={false}
                tickFormatter={(v) => v.toFixed(2)}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                formatter={(value: number) => [value, "Count"]}
                labelFormatter={(label) => `Value: ${Number(label).toFixed(4)}`}
              />
              <ReferenceLine
                x={spreadMean}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: "Mean", position: "top", fill: "#ef4444", fontSize: 10 }}
              />
              <ReferenceLine
                x={spreadMedian}
                stroke="#c28b00"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: "Median", position: "top", fill: "#c28b00", fontSize: 10 }}
              />
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {spreadBins.map((_, i) => (
                  <Cell
                    key={`spread-${i}`}
                    fill="rgba(194,139,0,0.6)"
                    stroke="rgba(194,139,0,0.2)"
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Z-Score Distribution */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-neutral-300 mb-1">
          Z-Score Distribution
        </h3>
        <p className="text-xs text-neutral-500 mb-4">
          Histogram of z-score values — tails beyond ±2 highlighted
        </p>
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={zscoreBins} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis
                dataKey="mid"
                tick={AXIS_TICK}
                axisLine={AXIS_LINE}
                tickLine={false}
                tickFormatter={(v) => v.toFixed(1)}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                formatter={(value: number) => [value, "Count"]}
                labelFormatter={(label) => `Z-Score: ${Number(label).toFixed(2)}`}
              />
              <ReferenceLine
                x={2}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: "+2σ", position: "top", fill: "#ef4444", fontSize: 10 }}
              />
              <ReferenceLine
                x={-2}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: "-2σ", position: "top", fill: "#ef4444", fontSize: 10 }}
              />
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {zscoreBins.map((bin, i) => (
                  <Cell
                    key={`zscore-${i}`}
                    fill={
                      bin.mid > 2 || bin.mid < -2
                        ? "rgba(239,68,68,0.6)"
                        : "rgba(34,197,94,0.5)"
                    }
                    stroke={
                      bin.mid > 2 || bin.mid < -2
                        ? "rgba(239,68,68,0.3)"
                        : "rgba(34,197,94,0.2)"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
