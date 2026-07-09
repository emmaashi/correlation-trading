"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  PairInfo,
  PAIRS,
  SECTOR_COLORS,
} from "@/lib/correlationTypes";
import SignalBadge from "./SignalBadge";
import type { SignalLevel } from "@/lib/correlationTypes";

interface PairSelectorProps {
  onSelect: (pair: PairInfo) => void;
  selectedPair: PairInfo | null;
  pairSignals: Record<string, SignalLevel>;
  onError: (message: string) => void;
}

export default function PairSelector({
  onSelect,
  selectedPair,
  pairSignals,
  onError,
}: PairSelectorProps) {
  const [customA, setCustomA] = useState("");
  const [customB, setCustomB] = useState("");
  const [validating, setValidating] = useState(false);

  const isSelected = (p: PairInfo) =>
    selectedPair?.ticker_a === p.ticker_a && selectedPair?.ticker_b === p.ticker_b;

  const handleCustomAnalyze = async () => {
    const a = customA.trim().toUpperCase();
    const b = customB.trim().toUpperCase();
    if (!a || !b || a === b) return;

    setValidating(true);
    try {
      const [resA, resB] = await Promise.all([
        fetch(`/api/validate?ticker=${a}`),
        fetch(`/api/validate?ticker=${b}`),
      ]);
      const dataA = await resA.json();
      const dataB = await resB.json();

      const invalid: string[] = [];
      if (!dataA.valid) invalid.push(a);
      if (!dataB.valid) invalid.push(b);

      if (invalid.length > 0) {
        onError(
          invalid.length === 2
            ? `"${invalid[0]}" and "${invalid[1]}" are not valid ticker symbols`
            : `"${invalid[0]}" is not a valid ticker symbol`
        );
        return;
      }

      onSelect({
        ticker_a: a,
        ticker_b: b,
        name_a: dataA.name ?? a,
        name_b: dataB.name ?? b,
        sector: "Custom",
      });
    } catch {
      onError("Could not validate tickers. Please try again.");
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h1 className="text-3xl sm:text-4xl font-bold text-neutral-50 tracking-tight">
          Correlation Trading
        </h1>
        <p className="text-neutral-400 text-sm sm:text-base max-w-xl mx-auto">
          Analyze lagged correlations, spread dynamics, and statistical trading
          signals between stock pairs.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {PAIRS.map((pair) => {
          const key = `${pair.ticker_a}_${pair.ticker_b}`;
          const signal = pairSignals[key];
          const selected = isSelected(pair);
          const sectorColor = SECTOR_COLORS[pair.sector] ?? "#888";

          return (
            <motion.button
              key={key}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={() => onSelect(pair)}
              className={`relative text-left rounded-2xl p-4 transition-all duration-200 border ${
                selected
                  ? "border-[#c28b00] bg-[#56461a]/20 shadow-[0_0_20px_rgba(194,139,0,0.15)]"
                  : "border-white/[0.08] bg-white/[0.03] hover:border-white/[0.15] hover:bg-white/[0.05]"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1.5 min-w-0">
                  <div className="text-neutral-50 font-semibold text-sm truncate">
                    {pair.name_a}
                    <span className="text-neutral-500 font-normal"> vs </span>
                    {pair.name_b}
                  </div>
                  <div className="flex gap-1.5">
                    <span className="px-2 py-0.5 rounded-md bg-white/[0.08] text-[11px] font-mono text-neutral-300">
                      {pair.ticker_a}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-white/[0.08] text-[11px] font-mono text-neutral-300">
                      {pair.ticker_b}
                    </span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                  <span
                    className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                    style={{ backgroundColor: `${sectorColor}20`, color: sectorColor }}
                  >
                    {pair.sector}
                  </span>
                  {signal && <SignalBadge level={signal} size="sm" />}
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Custom pair input */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <div className="h-3 w-3 rounded-full bg-neutral-500" />
          <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
            Custom Pair
          </h2>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 items-end">
          <div className="flex-1 w-full sm:w-auto">
            <label className="block text-xs text-neutral-500 mb-1 pl-1">
              Ticker A
            </label>
            <input
              value={customA}
              onChange={(e) => setCustomA(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL"
              className="w-full rounded-xl bg-white/[0.05] border border-white/[0.08] px-4 py-2.5 text-sm text-neutral-50 font-mono placeholder:text-neutral-600 focus:outline-none focus:border-[#c28b00]/50 focus:ring-1 focus:ring-[#c28b00]/30 transition-colors"
            />
          </div>
          <div className="flex-1 w-full sm:w-auto">
            <label className="block text-xs text-neutral-500 mb-1 pl-1">
              Ticker B
            </label>
            <input
              value={customB}
              onChange={(e) => setCustomB(e.target.value.toUpperCase())}
              placeholder="e.g. MSFT"
              className="w-full rounded-xl bg-white/[0.05] border border-white/[0.08] px-4 py-2.5 text-sm text-neutral-50 font-mono placeholder:text-neutral-600 focus:outline-none focus:border-[#c28b00]/50 focus:ring-1 focus:ring-[#c28b00]/30 transition-colors"
            />
          </div>
          <button
            onClick={handleCustomAnalyze}
            disabled={validating || !customA.trim() || !customB.trim() || customA.trim() === customB.trim()}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-[#c28b00] text-black font-semibold text-sm hover:bg-[#d4a020] disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {validating && (
              <div className="h-3.5 w-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
            )}
            {validating ? "Validating..." : "Analyze"}
          </button>
        </div>
      </div>
    </div>
  );
}
