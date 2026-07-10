"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { CorrelationPoint } from "@/lib/correlationTypes";

interface LagCorrelationChartProps {
  data: CorrelationPoint[];
  tickerA: string;
  tickerB: string;
}

function corrColor(val: number | null): string {
  if (val == null) return "#6b7280";
  if (val > 0.7) return "#22c55e";
  if (val > 0.3) return "#86efac";
  if (val > -0.3) return "#9ca3af";
  if (val > -0.7) return "#fca5a5";
  return "#ef4444";
}

export default function LagCorrelationChart({
  data,
  tickerA,
  tickerB,
}: LagCorrelationChartProps) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
      <h3 className="text-sm font-semibold text-neutral-300 mb-1">
        Lagged Correlation
      </h3>
      <p className="text-xs text-neutral-500 mb-4">
        Pearson correlation at different day-lags between {tickerA} and {tickerB}
      </p>

      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="lag"
              tick={{ fill: "#737373", fontSize: 11 }}
              axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
              tickLine={false}
              label={{
                value: "Lag (days)",
                position: "insideBottom",
                offset: -2,
                fill: "#737373",
                fontSize: 11,
              }}
            />
            <YAxis
              domain={[-1, 1]}
              tick={{ fill: "#737373", fontSize: 11 }}
              axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
              tickLine={false}
              label={{
                value: "Correlation",
                angle: -90,
                position: "insideLeft",
                offset: 10,
                fill: "#737373",
                fontSize: 11,
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(0,0,0,0.85)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "12px",
                backdropFilter: "blur(12px)",
                fontSize: 12,
                color: "#e5e5e5",
              }}
              formatter={(value: number) => [
                value?.toFixed(4) ?? "N/A",
                "Correlation",
              ]}
              labelFormatter={(label) => `Lag: ${label} day${Math.abs(label) !== 1 ? "s" : ""}`}
            />
            <ReferenceLine
              x={0}
              stroke="rgba(255,255,255,0.15)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            <ReferenceLine
              y={0}
              stroke="rgba(255,255,255,0.08)"
              strokeWidth={1}
            />
            <Line
              type="monotone"
              dataKey="correlation"
              stroke="#c28b00"
              strokeWidth={2}
              dot={(props: any) => {
                const { cx, cy, payload } = props;
                const color = corrColor(payload.correlation);
                return (
                  <circle
                    key={`dot-${payload.lag}`}
                    cx={cx}
                    cy={cy}
                    r={4}
                    fill={color}
                    stroke="rgba(0,0,0,0.3)"
                    strokeWidth={1}
                  />
                );
              }}
              activeDot={{
                r: 6,
                stroke: "#c28b00",
                strokeWidth: 2,
                fill: "#000",
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
