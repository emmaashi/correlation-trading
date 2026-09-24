"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

import PairSelector from "@/components/correlation/PairSelector";
import ControlsBar from "@/components/correlation/ControlsBar";
import LagCorrelationChart from "@/components/correlation/LagCorrelationChart";
import SpreadAnalysisCharts from "@/components/correlation/SpreadAnalysisCharts";
import MetricsPanel from "@/components/correlation/MetricsPanel";
import SpreadHistogram from "@/components/correlation/SpreadHistogram";
import Toast from "@/components/correlation/Toast";
import RiskWarningBanner from "@/components/correlation/RiskWarningBanner";
import BacktestControls, { BacktestParams } from "@/components/correlation/BacktestControls";
import BacktestResults from "@/components/correlation/BacktestResults";
import PairExplorerSkeleton from "@/components/correlation/PairExplorerSkeleton";

import type {
  PairInfo,
  CorrelationResponse,
  RiskBreakdownResponse,
  SpreadResponse,
  BacktestResponse,
  TradingSignalSummary,
} from "@/lib/correlationTypes";
import {
  getSignalDirection,
  PAIRS,
  SIGNAL_WINDOW,
} from "@/lib/correlationTypes";
import { todayISO, yearsAgoISO } from "@/lib/dateUtils";

const API_BASE = "/api";

export default function CorrelationTradingPage() {
  const [selectedPair, setSelectedPair] = useState<PairInfo | null>(null);
  const [dateRange, setDateRange] = useState({
    start: yearsAgoISO(3),
    end: todayISO(),
  });
  const [loading, setLoading] = useState(false);
  const [corrData, setCorrData] = useState<CorrelationResponse | null>(null);
  const [spreadData, setSpreadData] = useState<SpreadResponse | null>(null);
  const [riskData, setRiskData] = useState<RiskBreakdownResponse | null>(null);
  const [pairSignals, setPairSignals] = useState<
    Record<string, TradingSignalSummary | null>
  >({});
  const [loadingPairSignals, setLoadingPairSignals] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);

  const [backtestData, setBacktestData] = useState<BacktestResponse | null>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  const fetchAnalysis = useCallback(
    async (pair: PairInfo) => {
      const signalKey = `${pair.ticker_a}_${pair.ticker_b}`;
      setLoading(true);
      setError(null);
      setCorrData(null);
      setSpreadData(null);
      setRiskData(null);
      setPairSignals((prev) => ({ ...prev, [signalKey]: null }));

      try {
        const [corrRes, spreadRes, riskRes] = await Promise.all([
          fetch(
            `${API_BASE}/correlation?ticker_a=${pair.ticker_a}&ticker_b=${pair.ticker_b}&start=${dateRange.start}&end=${dateRange.end}`
          ),
          fetch(
            `${API_BASE}/spread?ticker_a=${pair.ticker_a}&ticker_b=${pair.ticker_b}&start=${dateRange.start}&end=${dateRange.end}&spread_type=log_ratio&window=${SIGNAL_WINDOW}`
          ),
          fetch(
            `${API_BASE}/risk/breakdown?ticker_a=${pair.ticker_a}&ticker_b=${pair.ticker_b}&end=${dateRange.end}`
          ),
        ]);

        if (!corrRes.ok || !spreadRes.ok) {
          let msg = `Could not load data for ${pair.ticker_a}/${pair.ticker_b}`;
          try {
            const errBody = await (corrRes.ok ? spreadRes : corrRes).json();
            if (errBody.error) msg = errBody.error;
          } catch {
            // response wasn't JSON
          }
          throw new Error(msg);
        }

        const corr: CorrelationResponse = await corrRes.json();
        const spread: SpreadResponse = await spreadRes.json();
        const risk: RiskBreakdownResponse | null = riskRes.ok
          ? await riskRes.json()
          : null;

        setCorrData(corr);
        setSpreadData(spread);
        setRiskData(risk);

        const zscore = spread.metrics.current_zscore;
        const direction = getSignalDirection(zscore);
        setPairSignals((prev) => {
          const next = { ...prev };
          next[signalKey] =
            zscore !== null && direction !== null
              ? {
                  ticker_a: pair.ticker_a,
                  ticker_b: pair.ticker_b,
                  zscore,
                  direction,
                  window: spread.metrics.zscore_window,
                }
              : null;
          return next;
        });
      } catch (e: any) {
        const msg = e.message ?? "Failed to load data";
        setError(msg);
        setToast({ message: msg, type: "error" });
      } finally {
        setLoading(false);
      }
    },
    [dateRange]
  );

  useEffect(() => {
    if (selectedPair) return;

    const controller = new AbortController();
    setPairSignals({});
    setLoadingPairSignals(true);

    const loadSignal = async (pair: PairInfo) => {
      const key = `${pair.ticker_a}_${pair.ticker_b}`;
      const params = new URLSearchParams({
        ticker_a: pair.ticker_a,
        ticker_b: pair.ticker_b,
        start: dateRange.start,
        end: dateRange.end,
        window: String(SIGNAL_WINDOW),
      });

      try {
        const response = await fetch(`${API_BASE}/signal?${params}`, {
          signal: controller.signal,
        });
        const payload = await response.json();
        const signal =
          response.ok &&
          typeof payload.zscore === "number" &&
          Number.isFinite(payload.zscore) &&
          ["short", "long", "hold"].includes(payload.direction)
            ? (payload as TradingSignalSummary)
            : null;

        setPairSignals((prev) => ({ ...prev, [key]: signal }));
      } catch (error) {
        if (!controller.signal.aborted) {
          setPairSignals((prev) => ({ ...prev, [key]: null }));
        }
      }
    };

    void Promise.allSettled(PAIRS.map(loadSignal)).finally(() => {
      if (!controller.signal.aborted) setLoadingPairSignals(false);
    });

    return () => controller.abort();
  }, [selectedPair, dateRange]);

  useEffect(() => {
    if (selectedPair) {
      fetchAnalysis(selectedPair);
    }
  }, [selectedPair, dateRange, fetchAnalysis]);

  const handleSelect = (pair: PairInfo) => {
    setSelectedPair(pair);
  };

  const handleBack = () => {
    setSelectedPair(null);
    setCorrData(null);
    setSpreadData(null);
    setRiskData(null);
    setError(null);
    setBacktestData(null);
  };

  const runBacktest = async (params: BacktestParams) => {
    if (!selectedPair) return;
    setBacktestLoading(true);
    setBacktestError(null);
    try {
      const res = await fetch(
        `${API_BASE}/backtest?ticker_a=${selectedPair.ticker_a}&ticker_b=${selectedPair.ticker_b}&start=${dateRange.start}&end=${dateRange.end}&spread_type=log_ratio&window=${params.window}&entry_z=${params.entry_z}&exit_z=${params.exit_z}&hedge_ratio=${params.hedge_ratio}`
      );
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.error || "Failed to run backtest");
      }
      const data: BacktestResponse = await res.json();
      setBacktestData(data);
    } catch (e: any) {
      setBacktestError(e.message || "Backtest failed");
    } finally {
      setBacktestLoading(false);
    }
  };

  if (!selectedPair && loadingPairSignals) {
    return <PairExplorerSkeleton />;
  }

  return (
    <main className="mx-6 sm:mx-0 min-h-screen bg-black text-neutral-50">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <div className="max-w-6xl mx-auto min-h-[calc(100vh-68px)] px-4 pb-8 sm:px-6">
        <AnimatePresence initial={false} mode="wait">
          {!selectedPair ? (
            <motion.div
              key="selector"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
            >
              <PairSelector
                onSelect={handleSelect}
                selectedPair={selectedPair}
                pairSignals={pairSignals}
                loadingPairSignals={loadingPairSignals}
                dateRange={dateRange}
                onError={(msg) => setToast({ message: msg, type: "error" })}
              />
            </motion.div>
          ) : (
            <motion.div
              key="analysis"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
            >
              <ControlsBar
                pair={selectedPair}
                dateRange={dateRange}
                onDateRangeChange={setDateRange}
                onBack={handleBack}
                loading={loading}
              />

              {error && (
                <div className="mt-6 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400 text-center">
                  {error}
                </div>
              )}

              {loading && !corrData && (
                <div className="mt-20 text-center">
                  <div className="inline-block h-8 w-8 border-2 border-neutral-700 border-t-[#c28b00] rounded-full animate-spin" />
                  <p className="text-neutral-500 text-sm mt-3">
                    Fetching data for {selectedPair.ticker_a}/{selectedPair.ticker_b}...
                  </p>
                </div>
              )}

              {spreadData && (
                <div className="mt-6 space-y-6">
                  {riskData?.broken && <RiskWarningBanner risk={riskData} />}

                  <MetricsPanel
                    metrics={spreadData.metrics}
                    model={spreadData.pair_model}
                  />

                  {corrData && (
                    <LagCorrelationChart
                      data={corrData.data}
                      tickerA={selectedPair.ticker_a}
                      tickerB={selectedPair.ticker_b}
                    />
                  )}

                  <SpreadAnalysisCharts
                    data={spreadData.data}
                    metrics={spreadData.metrics}
                    tickerA={selectedPair.ticker_a}
                    tickerB={selectedPair.ticker_b}
                  />

                  <SpreadHistogram
                    data={spreadData.data}
                    metrics={spreadData.metrics}
                  />

                  <BacktestControls
                    pair={selectedPair}
                    onRunBacktest={runBacktest}
                    loading={backtestLoading}
                    apiError={backtestError}
                  />
                  {backtestData && <BacktestResults data={backtestData} />}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
