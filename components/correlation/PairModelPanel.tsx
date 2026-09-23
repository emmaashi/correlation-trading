"use client";

import { useId, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown } from "lucide-react";

import type {
  PairModelRejectionReason,
  PairModelValidation,
} from "@/lib/correlationTypes";

interface PairModelPanelProps {
  model: PairModelValidation;
}

function rejectionLabel(
  reason: PairModelRejectionReason,
  model: PairModelValidation
): string {
  const labels: Record<PairModelRejectionReason, string> = {
    insufficient_history: `Fewer than ${model.thresholds.min_observations} aligned observations`,
    invalid_data: "Prices include missing, infinite, or nonpositive values",
    invalid_hedge_ratio: "Hedge ratio is invalid or nonpositive",
    cointegration_not_significant: "Engle-Granger threshold not met",
    residual_not_stationary: "Residual ADF threshold not met",
    non_mean_reverting: "Residual AR(1) dynamics are not mean reverting",
    implausible_half_life: `Half-life is outside ${model.thresholds.min_half_life_days}-${model.thresholds.max_half_life_days} days`,
  };
  return labels[reason];
}

export default function PairModelPanel({ model }: PairModelPanelProps) {
  const [open, setOpen] = useState(false);
  const contentId = useId();
  const StatusIcon = model.eligible ? CheckCircle2 : AlertTriangle;
  const label = model.eligible ? "Model checks" : "Model cautions";

  return (
    <div className="contents">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((value) => !value)}
        className={`ml-auto inline-flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
          model.eligible
            ? "text-neutral-400 hover:bg-white/[0.05] hover:text-neutral-200"
            : "text-amber-400 hover:bg-amber-400/[0.08] hover:text-amber-300"
        }`}
      >
        <span className="inline-flex items-center gap-1.5">
          <StatusIcon aria-hidden="true" className="h-3.5 w-3.5" />
          {label}
        </span>
        <ChevronDown
          aria-hidden="true"
          className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          id={contentId}
          className="mt-1 w-full basis-full border-t border-white/[0.06] px-2 pt-3"
        >
          {model.eligible ? (
            <p className="text-xs text-green-400">All model checks passed.</p>
          ) : (
            <ul className="space-y-1 text-xs text-amber-300/90">
              {model.rejection_reasons.map((reason) => (
                <li key={reason}>{rejectionLabel(reason, model)}</li>
              ))}
            </ul>
          )}
          <p className="mt-2 max-w-xl text-[11px] leading-relaxed text-neutral-500">
            These checks add context about whether the pair has historically
            behaved like a mean-reverting relationship. They do not override the
            trading signal or guarantee future performance.
          </p>
        </div>
      )}
    </div>
  );
}
