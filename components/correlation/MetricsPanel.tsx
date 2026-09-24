"use client";

import {
  SpreadMetrics,
  PairModelValidation,
  getSignalLevel,
  getSignalDirection,
  getSignalColor,
} from "@/lib/correlationTypes";
import ChartInfoTooltip from "./ChartInfoTooltip";
import PairModelPanel from "./PairModelPanel";
import SignalBadge from "./SignalBadge";

interface MetricsPanelProps {
  metrics: SpreadMetrics;
  model: PairModelValidation;
}

function Divider() {
  return <div className="w-px self-stretch bg-white/[0.06]" />;
}

export default function MetricsPanel({ metrics, model }: MetricsPanelProps) {
  const zscore = metrics.current_zscore;
  const level = getSignalLevel(zscore);
  const direction = getSignalDirection(zscore);
  const signalColor = level ? getSignalColor(level) : "#737373";
  const spreadWindowLabel = `${metrics.zscore_window}D`;
  const signalAvailable = level !== null;
  const tradeLegs =
    direction === "short"
      ? { short: metrics.ticker_a, long: metrics.ticker_b }
      : direction === "long"
        ? { short: metrics.ticker_b, long: metrics.ticker_a }
        : null;

  return (
    <section className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-y-2">
          <div className="flex items-center gap-2 px-2">
            <span className="text-[10px] uppercase tracking-widest text-neutral-500">
              Signal
            </span>
            <ChartInfoTooltip label="Trading Signal">
              Uses the pair&apos;s 60-day log-ratio z-score. At +2 or higher,
              short {metrics.ticker_a} and long {metrics.ticker_b}. At -2 or
              lower, take the reverse position. Otherwise, hold. This is a
              research signal, not a guarantee of mean reversion or profit.
            </ChartInfoTooltip>
            {!signalAvailable ? (
              <span className="text-[10px] font-semibold text-neutral-500">
                Unavailable
              </span>
            ) : tradeLegs ? (
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
              <SignalBadge level={level} size="sm" pulse={false} label="Hold" />
            )}
          </div>

          <Divider />

          <div className="flex items-center gap-1.5 px-2">
            <span className="text-[10px] uppercase tracking-widest text-neutral-500">
              {spreadWindowLabel} Z-Score
            </span>
            <span
              className="font-mono text-sm font-semibold tabular-nums"
              style={{ color: signalColor }}
            >
              {zscore === null ? "N/A" : zscore.toFixed(3)}
            </span>
          </div>

          <Divider />

          <div className="flex items-center gap-1.5 px-2">
            <span className="text-[10px] uppercase tracking-widest text-neutral-500">
              OBS
            </span>
            <ChartInfoTooltip label="Observations">
              Observations are aligned trading days with valid prices for both
              stocks in the selected date range. This is the full sample size;
              60D metrics use only the most recent 60 observations.
            </ChartInfoTooltip>
            <span className="font-mono text-sm tabular-nums text-neutral-300">
              {metrics.num_observations.toLocaleString()}
            </span>
          </div>
        </div>

        <PairModelPanel model={model} />
      </div>
    </section>
  );
}
