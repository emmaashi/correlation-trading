"use client";

import { SpreadMetrics, getSignalLevel, getSignalDirection, getSignalColor } from "@/lib/correlationTypes";
import SignalBadge from "./SignalBadge";

interface MetricsPanelProps {
  metrics: SpreadMetrics;
}

function Divider() {
  return <div className="w-px self-stretch bg-white/[0.06]" />;
}

export default function MetricsPanel({ metrics }: MetricsPanelProps) {
  const zscore = metrics.current_zscore;
  const level = getSignalLevel(zscore);
  const direction = getSignalDirection(zscore);
  const signalColor = getSignalColor(level);
  const zscoreWindowLabel = metrics.zscore_window ? `${metrics.zscore_window}D` : "Full";
  const currentMean = metrics.current_mean ?? metrics.mean;
  const currentStd = metrics.current_std ?? metrics.std;
  const tradeLegs =
    direction === "short"
      ? { short: metrics.ticker_a, long: metrics.ticker_b }
      : direction === "long"
        ? { short: metrics.ticker_b, long: metrics.ticker_a }
        : null;

  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-2 py-2.5">
      <div className="flex flex-wrap items-center gap-y-2">
        {/* Signal */}
        <div className="flex items-center gap-2 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">Signal</span>
          {tradeLegs ? (
            <div className="flex items-center gap-2 text-[10px] font-semibold">
              <span className="inline-flex items-center gap-1.5 text-red-400">
                <span className="h-2 w-2 rounded-full bg-red-500" />
                Short <span className="font-mono">{tradeLegs.short}</span>
              </span>
              <span className="text-neutral-600">+</span>
              <span className="inline-flex items-center gap-1.5 text-green-400">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                Long <span className="font-mono">{tradeLegs.long}</span>
              </span>
            </div>
          ) : (
            <SignalBadge level={level} size="sm" pulse={false} label="No Trade" />
          )}
        </div>

        <Divider />

        {/* Z-Score */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">{zscoreWindowLabel} Z-Score</span>
          <span className="text-sm font-mono tabular-nums font-semibold" style={{ color: signalColor }}>
            {zscore.toFixed(3)}
          </span>
        </div>

        <Divider />

        {/* Current Spread */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">Spread</span>
          <span className="text-sm font-mono tabular-nums font-semibold text-neutral-200">
            {metrics.current.toFixed(4)}
          </span>
          <span className="text-[10px] text-neutral-500">
            {metrics.current > currentMean ? "↑" : "↓"}
          </span>
        </div>

        <Divider />

        {/* Mean */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">{zscoreWindowLabel} Mean</span>
          <span className="text-sm font-mono tabular-nums text-neutral-300">{currentMean.toFixed(4)}</span>
        </div>

        <Divider />

        {/* Std Dev */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">{zscoreWindowLabel} Std</span>
          <span className="text-sm font-mono tabular-nums text-neutral-300">{currentStd.toFixed(4)}</span>
        </div>

        <Divider />

        {/* Observations */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">Obs</span>
          <span className="text-sm font-mono tabular-nums text-neutral-300">{metrics.num_observations.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
