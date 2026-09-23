"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, Loader2, RefreshCw } from "lucide-react";

import type { StrategyBacktestResponse } from "@/lib/strategyTypes";
import { BacktestDetail, responseJson } from "./StrategyLab";

interface StrategyCandidateDetailProps {
  target: string;
  peers: string[];
  start: string;
  end: string;
  backHref: string;
}

export default function StrategyCandidateDetail({
  target,
  peers,
  start,
  end,
  backHref,
}: StrategyCandidateDetailProps) {
  const [result, setResult] = useState<StrategyBacktestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const runBacktest = useCallback(
    async (signal: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/strategy/backtest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target,
            peers,
            start,
            end,
            initial_capital: 100000,
            gross_exposure: 1,
            transaction_cost_bps: 5,
            annual_borrow_rate: 0.03,
            participation_rate: 0.01,
          }),
          signal,
        });
        setResult(await responseJson<StrategyBacktestResponse>(response));
      } catch (requestError: any) {
        if (!signal.aborted) {
          setError(requestError.message ?? "Could not run the strategy backtest");
        }
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    },
    [end, peers, start, target]
  );

  useEffect(() => {
    const controller = new AbortController();
    void runBacktest(controller.signal);
    return () => controller.abort();
  }, [attempt, runBacktest]);

  return (
    <div className="pt-7 sm:pt-9">
      <header className="border-b border-white/[0.08] pb-5">
        <Link
          href={backHref}
          className="inline-flex h-8 items-center gap-2 rounded-md px-2 text-xs font-medium text-neutral-500 transition-colors hover:bg-white/[0.05] hover:text-neutral-100 focus:outline-none focus-visible:ring-1 focus-visible:ring-[#c28b00]/70"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          Back to Strategy Lab
        </Link>
        <div className="mt-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[10px] font-medium uppercase text-neutral-600">Candidate analysis</p>
            <h1 className="mt-1 font-mono text-2xl font-semibold text-neutral-50 sm:text-3xl">{target}</h1>
          </div>
          <p className="max-w-2xl text-xs leading-5 text-neutral-500 sm:text-right">
            Compared with {peers.join(", ")} from {start} through {end}
          </p>
        </div>
      </header>

      {loading && (
        <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-neutral-500">
          <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
          Running three walk-forward simulations for {target}
        </div>
      )}

      {!loading && error && (
        <div className="mt-8 flex min-h-52 flex-col items-center justify-center gap-4 rounded-lg border border-red-500/20 bg-red-500/[0.05] px-5 text-center">
          <AlertTriangle aria-hidden="true" className="h-5 w-5 text-red-400" />
          <div>
            <h2 className="text-sm font-semibold text-red-200">Candidate analysis could not load</h2>
            <p className="mt-1 text-xs text-red-300/70">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => setAttempt((current) => current + 1)}
            className="inline-flex h-8 items-center gap-2 rounded-md border border-red-400/25 px-3 text-xs font-medium text-red-200 transition-colors hover:bg-red-400/10"
          >
            <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
            Try again
          </button>
        </div>
      )}

      {result && <BacktestDetail result={result} className="mt-7" />}

      <div className="mt-8 flex items-start gap-2 border-t border-white/[0.08] pt-4 text-[11px] leading-5 text-neutral-600">
        <AlertTriangle aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
        <p>
          Research simulation only. This candidate view is not investment advice, risk-free arbitrage, or a guarantee of future performance.
        </p>
      </div>
    </div>
  );
}
