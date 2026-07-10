"use client";

import { AlertTriangle } from "lucide-react";

import type { RiskBreakdownResponse } from "@/lib/correlationTypes";

interface RiskWarningBannerProps {
  risk: RiskBreakdownResponse;
}

function formatCorrelation(value: number | null): string {
  return value === null ? "N/A" : value.toFixed(3);
}

export default function RiskWarningBanner({ risk }: RiskWarningBannerProps) {
  return (
    <div className="rounded-xl border border-amber-500/25 bg-amber-500/[0.08] px-4 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" />
          <div>
            <p className="text-sm font-semibold text-amber-100">
              Correlation breakdown detected for {risk.ticker_a}/{risk.ticker_b}
            </p>
            <p className="mt-1 text-xs text-amber-100/70">
              Recent 60d correlation is below the historical baseline.
              {risk.broken_since ? ` Broken since ${risk.broken_since}.` : ""}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="font-mono tabular-nums text-amber-100">
            Current {formatCorrelation(risk.current_corr)}
          </span>
          <span className="font-mono tabular-nums text-amber-100/70">
            Baseline {formatCorrelation(risk.baseline_corr)}
          </span>
        </div>
      </div>
    </div>
  );
}
