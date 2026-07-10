"use client";

import { PairInfo, SECTOR_COLORS } from "@/lib/correlationTypes";

interface ControlsBarProps {
  pair: PairInfo;
  dateRange: { start: string; end: string };
  spreadType: string;
  onDateRangeChange: (range: { start: string; end: string }) => void;
  onSpreadTypeChange: (type: string) => void;
  onBack: () => void;
  loading: boolean;
}

const PRESETS = [
  { label: "1Y", years: 1 },
  { label: "2Y", years: 2 },
  { label: "3Y", years: 3 },
  { label: "5Y", years: 5 },
  { label: "Max", years: 10 },
];

const SPREAD_TYPES = [
  { value: "log_ratio", label: "Log Ratio" },
  { value: "ratio", label: "Ratio" },
  { value: "difference", label: "Difference" },
];

function yearsAgo(n: number): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return d.toISOString().split("T")[0];
}

export default function ControlsBar({
  pair,
  dateRange,
  spreadType,
  onDateRangeChange,
  onSpreadTypeChange,
  onBack,
  loading,
}: ControlsBarProps) {
  const activePreset = PRESETS.find((p) => dateRange.start === yearsAgo(p.years));
  const sectorColor = SECTOR_COLORS[pair.sector] ?? "#888";

  return (
    <div className="sticky top-0 z-40 -mx-6 sm:-mx-0">
      <div className="backdrop-blur-xl bg-black/70 border-b border-white/[0.06] px-4 sm:px-6 py-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 max-w-6xl mx-auto">
          {/* Back + pair info */}
          <div className="flex items-center gap-3 min-w-0 flex-shrink-0">
            <button
              onClick={onBack}
              className="text-neutral-400 hover:text-neutral-50 transition-colors text-sm"
            >
              ← Back
            </button>
            <div className="h-4 w-px bg-white/10" />
            <div className="flex items-center gap-2 min-w-0">
              <div
                className="h-2 w-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: sectorColor }}
              />
              <span className="text-neutral-50 font-semibold text-sm truncate">
                {pair.name_a}
                <span className="text-neutral-500 font-normal"> / </span>
                {pair.name_b}
              </span>
              <span className="text-[10px] font-mono text-neutral-500 flex-shrink-0">
                {pair.ticker_a}/{pair.ticker_b}
              </span>
            </div>
          </div>

          <div className="flex-1" />

          {/* Date presets */}
          <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() =>
                  onDateRangeChange({
                    start: yearsAgo(p.years),
                    end: new Date().toISOString().split("T")[0],
                  })
                }
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  activePreset?.label === p.label
                    ? "bg-white/[0.12] text-neutral-50"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Spread type */}
          <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
            {SPREAD_TYPES.map((st) => (
              <button
                key={st.value}
                onClick={() => onSpreadTypeChange(st.value)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  spreadType === st.value
                    ? "bg-white/[0.12] text-neutral-50"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          {loading && (
            <div className="flex items-center gap-2 text-xs text-neutral-500">
              <div className="h-3 w-3 border-2 border-neutral-600 border-t-[#c28b00] rounded-full animate-spin" />
              Loading
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
