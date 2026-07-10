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

  const signalLabel =
    direction === "long" ? "Long" : direction === "short" ? "Short" : "Hold";

  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-2 py-2.5">
      <div className="flex flex-wrap items-center gap-y-2">
        {/* Signal */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">Signal</span>
          <SignalBadge level={level} size="sm" pulse={false} label={signalLabel} />
        </div>

        <Divider />

        {/* Z-Score */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">Z-Score</span>
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
            {metrics.current > metrics.mean ? "↑" : "↓"}
          </span>
        </div>

        <Divider />

        {/* Mean */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">Mean</span>
          <span className="text-sm font-mono tabular-nums text-neutral-300">{metrics.mean.toFixed(4)}</span>
        </div>

        <Divider />

        {/* Std Dev */}
        <div className="flex items-center gap-1.5 px-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-500">Std</span>
          <span className="text-sm font-mono tabular-nums text-neutral-300">{metrics.std.toFixed(4)}</span>
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
