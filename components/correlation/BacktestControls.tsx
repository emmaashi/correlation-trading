"use client";

import { useState } from "react";
import { PairInfo } from "@/lib/correlationTypes";

export interface BacktestParams {
  window: number;
  entry_z: number;
  exit_z: number;
  hedge_ratio: number;
}

interface BacktestControlsProps {
  pair: PairInfo;
  onRunBacktest: (params: BacktestParams) => void;
  loading: boolean;
  apiError?: string | null;
}

export default function BacktestControls({
  pair,
  onRunBacktest,
  loading,
  apiError,
}: BacktestControlsProps) {
  const [localError, setLocalError] = useState<string | null>(null);
  const [params, setParams] = useState<{
    window: number | "";
    entry_z: number | "";
    exit_z: number | "";
    hedge_ratio: number | "";
  }>({
    window: 60,
    entry_z: 2.0,
    exit_z: 0.0,
    hedge_ratio: 1.0,
  });

  const handleChange = (key: keyof BacktestParams, value: string) => {
    if (value === "") {
      setParams((prev) => ({ ...prev, [key]: "" }));
      return;
    }
    const parsed = parseFloat(value);
    setParams((prev) => ({
      ...prev,
      [key]: isNaN(parsed) ? prev[key] : parsed,
    }));
  };

  const handleRun = () => {
    if ((params.exit_z as number) >= (params.entry_z as number)) {
      setLocalError("Exit Z-Score must be strictly less than Entry Z-Score.");
      return;
    }
    
    setLocalError(null); 
    onRunBacktest({
      window: params.window as number,
      entry_z: params.entry_z as number,
      exit_z: params.exit_z as number,
      hedge_ratio: params.hedge_ratio as number,
    });
  };

  return (
    <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-4 mt-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-neutral-50 font-medium text-sm">Backtest Engine</h3>
          <p className="text-neutral-500 text-xs mt-1">
            Run a walk-forward simulation using rolling z-scores on {pair.ticker_a}/{pair.ticker_b}.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-neutral-400 uppercase tracking-wider">Window</label>
            <input
              type="number"
              value={params.window}
              onChange={(e) => handleChange("window", e.target.value)}
              className="bg-black border border-white/10 rounded-md px-2 py-1 text-sm text-neutral-200 w-20 focus:outline-none focus:border-white/20"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-neutral-400 uppercase tracking-wider">Entry Z</label>
            <input
              type="number"
              step="0.1"
              value={params.entry_z}
              onChange={(e) => handleChange("entry_z", e.target.value)}
              className="bg-black border border-white/10 rounded-md px-2 py-1 text-sm text-neutral-200 w-20 focus:outline-none focus:border-white/20"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-neutral-400 uppercase tracking-wider">Exit Z</label>
            <input
              type="number"
              step="0.1"
              value={params.exit_z}
              onChange={(e) => handleChange("exit_z", e.target.value)}
              className="bg-black border border-white/10 rounded-md px-2 py-1 text-sm text-neutral-200 w-20 focus:outline-none focus:border-white/20"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-neutral-400 uppercase tracking-wider">Hedge Ratio</label>
            <input
              type="number"
              step="0.1"
              value={params.hedge_ratio}
              onChange={(e) => handleChange("hedge_ratio", e.target.value)}
              className="bg-black border border-white/10 rounded-md px-2 py-1 text-sm text-neutral-200 w-24 focus:outline-none focus:border-white/20"
            />
          </div>
          
          <div className="flex flex-col gap-1 self-end">
            <button
              onClick={handleRun}
              disabled={loading}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                loading
                  ? "bg-white/10 text-neutral-500 cursor-not-allowed"
                  : "bg-white text-black hover:bg-neutral-200"
              }`}
            >
              {loading ? "Running..." : "Run Backtest"}
            </button>
          </div>
        </div>
      </div>
      
      {(localError || apiError) && (
        <p className="text-red-400 text-xs mt-4">
          {localError || apiError}
        </p>
      )}
    </div>
  );
}
