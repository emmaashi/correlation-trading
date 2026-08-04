"use client";

import { AlertTriangle } from "lucide-react";

import type { RiskBreakdownResponse } from "@/lib/correlationTypes";

interface RiskWarningBannerProps {
  risk: RiskBreakdownResponse;
}

function formatCorrelation(value: number | null): string {
  return value === null ? "N/A" : value.toFixed(3);
}

function formatDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(year, month - 1, day));
}

export default function RiskWarningBanner({ risk }: RiskWarningBannerProps) {
  return (
    <div
      role="status"
      className="rounded-lg border border-white/[0.08] border-l-2 border-l-amber-400/70 bg-white/[0.025] px-4 py-3"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-amber-400/10">
            <AlertTriangle className="h-4 w-4 text-amber-300" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-neutral-100">
              Correlation breakdown
            </p>
            <p className="mt-0.5 text-xs leading-5 text-neutral-500">
              {risk.ticker_a}/{risk.ticker_b}&apos;s 60-day correlation is below
              its historical baseline
              {risk.broken_since
                ? ` since ${formatDate(risk.broken_since)}.`
                : "."}
            </p>
          </div>
        </div>

        <div className="flex flex-shrink-0 items-center gap-5 border-t border-white/[0.06] pt-3 sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0">
          <div>
            <p className="text-[10px] font-medium uppercase text-neutral-600">
              Current
            </p>
            <p className="mt-0.5 font-mono text-sm tabular-nums text-amber-300">
              {formatCorrelation(risk.current_corr)}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-medium uppercase text-neutral-600">
              Baseline
            </p>
            <p className="mt-0.5 font-mono text-sm tabular-nums text-neutral-300">
              {formatCorrelation(risk.baseline_corr)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
