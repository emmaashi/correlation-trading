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
import {
  formatChartAxisDate,
  formatChartTooltipDate,
} from "@/lib/dateUtils";
import ChartInfoTooltip from "./ChartInfoTooltip";

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
  lineHeight: 1.2,
  padding: "10px 12px",
  color: "#e5e5e5",
};

const TOOLTIP_LABEL_STYLE = {
  color: "#f5f5f5",
  fontWeight: 600,
  marginBottom: 8,
};

const AXIS_TICK = { fill: "#737373", fontSize: 10 };
const AXIS_LINE = { stroke: "rgba(255,255,255,0.06)" };
const GRID = "rgba(255,255,255,0.04)";

type ChartTooltipPayload = {
  payload?: Record<string, unknown>;
};

type ChartTooltipProps = {
  active?: boolean;
  label?: string | number;
  payload?: ChartTooltipPayload[];
  rows: Array<{
    color: string;
    dataKey: string;
    label: string;
    precision: number;
  }>;
};

function getFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function ChartValueTooltip({ active, label, payload, rows }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const point = payload[0]?.payload;
  const values = rows.flatMap((row) => {
    const value = getFiniteNumber(point?.[row.dataKey]);
    return value === null ? [] : [{ ...row, value }];
  });

  if (!values.length) return null;

  return (
    <div style={TOOLTIP_STYLE}>
      <div style={TOOLTIP_LABEL_STYLE}>
        Date: {formatChartTooltipDate(String(label))}
      </div>
      <div style={{ display: "grid", gap: 6 }}>
        {values.map((row) => (
          <div key={row.dataKey} style={{ color: row.color, lineHeight: 1.2 }}>
            {row.label}: {row.value.toFixed(row.precision)}
          </div>
        ))}
      </div>
    </div>
  );
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

  return (
    <div className="space-y-4">
      {/* Normalized Prices */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <div className="mb-1 flex items-start gap-1.5">
          <h3 className="text-sm font-semibold text-neutral-300">
            Normalized Price Comparison
          </h3>
          <ChartInfoTooltip label="Normalized Price Comparison">
            Puts both stocks at the same starting value so you can see which has
            outperformed and when their returns diverge. A widening gap suggests
            relative momentum. A closing gap suggests mean reversion.
          </ChartInfoTooltip>
        </div>
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
                tickFormatter={formatChartAxisDate}
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                content={
                  <ChartValueTooltip
                    rows={[
                      {
                        color: "#c28b00",
                        dataKey: "norm_a",
                        label: tickerA,
                        precision: 2,
                      },
                      {
                        color: "#60a5fa",
                        dataKey: "norm_b",
                        label: tickerB,
                        precision: 2,
                      },
                    ]}
                  />
                }
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
        <div className="mb-1 flex items-start gap-1.5">
          <h3 className="text-sm font-semibold text-neutral-300">
            Spread with Mean Reversion Bands
          </h3>
          <ChartInfoTooltip label="Spread with Mean Reversion Bands">
            Tracks the selected spread of {tickerA} relative to {tickerB}. The
            center line is its historical mean; amber and red bands mark one and
            two standard deviations. Repeated moves back toward the mean support
            a mean-reversion thesis, while persistent breaks can signal a regime
            change.
          </ChartInfoTooltip>
        </div>
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
                tickFormatter={formatChartAxisDate}
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                content={
                  <ChartValueTooltip
                    rows={[
                      {
                        color: "#c28b00",
                        dataKey: "spread",
                        label: "Spread",
                        precision: 4,
                      },
                    ]}
                  />
                }
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
        <div className="mb-1 flex items-start gap-1.5">
          <h3 className="text-sm font-semibold text-neutral-300">
            Spread Z-Score
          </h3>
          <ChartInfoTooltip label="Spread Z-Score">
            Expresses the spread&apos;s distance from its rolling 60-day mean in
            standard deviations. Zero is typical, values beyond ±1 are worth
            watching, and moves beyond ±2 are potential pair-trade signals.
          </ChartInfoTooltip>
        </div>
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
                tickFormatter={formatChartAxisDate}
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
              <Tooltip
                content={
                  <ChartValueTooltip
                    rows={[
                      {
                        color: "#22c55e",
                        dataKey: "zscore",
                        label: "Z-Score",
                        precision: 3,
                      },
                    ]}
                  />
                }
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
