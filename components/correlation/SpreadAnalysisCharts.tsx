"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
} from "recharts";
import { SpreadPoint, SpreadMetrics } from "@/lib/correlationTypes";

interface SpreadAnalysisChartsProps {
  data: SpreadPoint[];
  metrics: SpreadMetrics;
  tickerA: string;
  tickerB: string;
}

const TOOLTIP_STYLE = {
  backgroundColor: "rgba(0,0,0,0.85)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "12px",
  backdropFilter: "blur(12px)",
  fontSize: 12,
  color: "#e5e5e5",
};

const AXIS_TICK = { fill: "#737373", fontSize: 10 };
const AXIS_LINE = { stroke: "rgba(255,255,255,0.06)" };
const GRID = "rgba(255,255,255,0.04)";

function formatDate(d: string) {
  const date = new Date(d);
  return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

export default function SpreadAnalysisCharts({
  data,
  metrics,
  tickerA,
  tickerB,
}: SpreadAnalysisChartsProps) {
  const mean = metrics.mean;
  const std = metrics.std;

  const enriched = data.map((d) => ({
    ...d,
    band1Upper: mean + std,
    band1Lower: mean - std,
    band2Upper: mean + 2 * std,
    band2Lower: mean - 2 * std,
    spreadMean: mean,
    zUpper: 2,
    zLower: -2,
    zZero: 0,
  }));

  const everyN = Math.max(1, Math.floor(data.length / 12));

  return (
    <div className="space-y-4">
      {/* Normalized Prices */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-neutral-300 mb-1">
          Normalized Price Comparison
        </h3>
        <p className="text-xs text-neutral-500 mb-4">
          Both stocks rebased to 100 at the start of the period
        </p>
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis
                dataKey="date"
                tick={AXIS_TICK}
                axisLine={AXIS_LINE}
                tickLine={false}
                tickFormatter={formatDate}
                interval={everyN}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(l) => `Date: ${l}`}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "#a3a3a3" }}
              />
              <Line
                type="monotone"
                dataKey="norm_a"
                name={tickerA}
                stroke="#c28b00"
                strokeWidth={1.5}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="norm_b"
                name={tickerB}
                stroke="#60a5fa"
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Spread with Bands */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-neutral-300 mb-1">
          Spread with Mean Reversion Bands
        </h3>
        <p className="text-xs text-neutral-500 mb-4">
          Spread value with ±1σ and ±2σ bands around the historical mean
        </p>
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={enriched} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis
                dataKey="date"
                tick={AXIS_TICK}
                axisLine={AXIS_LINE}
                tickLine={false}
                tickFormatter={formatDate}
                interval={everyN}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(l) => `Date: ${l}`}
                formatter={(value: number, name: string) => {
                  if (name === "spread") return [value?.toFixed(4), "Spread"];
                  return [null, ""];
                }}
              />
              {/* ±2σ band */}
              <ReferenceLine y={mean + 2 * std} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} strokeOpacity={0.5} />
              <ReferenceLine y={mean - 2 * std} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} strokeOpacity={0.5} />
              {/* ±1σ band */}
              <ReferenceLine y={mean + std} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} strokeOpacity={0.4} />
              <ReferenceLine y={mean - std} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} strokeOpacity={0.4} />
              {/* Mean */}
              <ReferenceLine y={mean} stroke="#ef4444" strokeDasharray="6 3" strokeWidth={1.5} strokeOpacity={0.7} />
              {/* ±1σ shaded area */}
              <Area
                type="monotone"
                dataKey="band1Upper"
                stroke="none"
                fill="transparent"
                activeDot={false}
              />
              <Area
                type="monotone"
                dataKey="band1Lower"
                stroke="none"
                fill="rgba(245,158,11,0.06)"
                activeDot={false}
              />
              <Line
                type="monotone"
                dataKey="spread"
                stroke="#c28b00"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 4, fill: "#c28b00" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Z-Score */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-neutral-300 mb-1">
          Spread Z-Score
        </h3>
        <p className="text-xs text-neutral-500 mb-4">
          Standardized spread — values beyond ±2 indicate potential trading signals
        </p>
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={enriched} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <defs>
                <linearGradient id="zscoreGreenFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.08} />
                  <stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis
                dataKey="date"
                tick={AXIS_TICK}
                axisLine={AXIS_LINE}
                tickLine={false}
                tickFormatter={formatDate}
                interval={everyN}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(l) => `Date: ${l}`}
                formatter={(value: number) => [value?.toFixed(3), "Z-Score"]}
              />
              {/* Thresholds */}
              <ReferenceLine y={2} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1.5} strokeOpacity={0.7} label={{ value: "+2σ", position: "right", fill: "#ef4444", fontSize: 10 }} />
              <ReferenceLine y={-2} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1.5} strokeOpacity={0.7} label={{ value: "-2σ", position: "right", fill: "#ef4444", fontSize: 10 }} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
              {/* Normal range fill */}
              <Area
                type="monotone"
                dataKey="zUpper"
                stroke="none"
                fill="transparent"
                activeDot={false}
              />
              <Area
                type="monotone"
                dataKey="zLower"
                stroke="none"
                fill="url(#zscoreGreenFill)"
                activeDot={false}
              />
              <Line
                type="monotone"
                dataKey="zscore"
                stroke="#22c55e"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 4, fill: "#22c55e" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
