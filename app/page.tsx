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

import type {
  PairInfo,
  CorrelationResponse,
  RiskBreakdownResponse,
  SpreadResponse,
  SignalLevel,
} from "@/lib/correlationTypes";
import { getSignalLevel } from "@/lib/correlationTypes";

const API_BASE = "/api";

function yearsAgo(n: number): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return d.toISOString().split("T")[0];
}

export default function CorrelationTradingPage() {
  const [selectedPair, setSelectedPair] = useState<PairInfo | null>(null);
  const [dateRange, setDateRange] = useState({
    start: yearsAgo(3),
    end: new Date().toISOString().split("T")[0],
  });
  const [spreadType, setSpreadType] = useState("log_ratio");
  const [loading, setLoading] = useState(false);
  const [corrData, setCorrData] = useState<CorrelationResponse | null>(null);
  const [spreadData, setSpreadData] = useState<SpreadResponse | null>(null);
  const [riskData, setRiskData] = useState<RiskBreakdownResponse | null>(null);
  const [pairSignals, setPairSignals] = useState<Record<string, SignalLevel>>({});
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);

  const fetchAnalysis = useCallback(
    async (pair: PairInfo) => {
      setLoading(true);
      setError(null);
      setCorrData(null);
      setSpreadData(null);
      setRiskData(null);

      try {
        const [corrRes, spreadRes, riskRes] = await Promise.all([
          fetch(
            `${API_BASE}/correlation?ticker_a=${pair.ticker_a}&ticker_b=${pair.ticker_b}&start=${dateRange.start}&end=${dateRange.end}`
          ),
          fetch(
            `${API_BASE}/spread?ticker_a=${pair.ticker_a}&ticker_b=${pair.ticker_b}&start=${dateRange.start}&end=${dateRange.end}&spread_type=${spreadType}`
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

        setPairSignals((prev) => ({
          ...prev,
          [`${pair.ticker_a}_${pair.ticker_b}`]: getSignalLevel(
            spread.metrics.current_zscore
          ),
        }));
      } catch (e: any) {
        const msg = e.message ?? "Failed to load data";
        setError(msg);
        setToast({ message: msg, type: "error" });
      } finally {
        setLoading(false);
      }
    },
    [dateRange, spreadType]
  );

  useEffect(() => {
    if (selectedPair) {
      fetchAnalysis(selectedPair);
    }
  }, [selectedPair, dateRange, spreadType, fetchAnalysis]);

  const handleSelect = (pair: PairInfo) => {
    setSelectedPair(pair);
  };

  const handleBack = () => {
    setSelectedPair(null);
    setCorrData(null);
    setSpreadData(null);
    setRiskData(null);
    setError(null);
  };

  return (
    <main className="mx-6 sm:mx-0 min-h-screen bg-black text-neutral-50">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 min-h-[calc(100vh-80px)]">
        <AnimatePresence mode="wait">
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
                spreadType={spreadType}
                onDateRangeChange={setDateRange}
                onSpreadTypeChange={setSpreadType}
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

                  <MetricsPanel metrics={spreadData.metrics} />

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
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
