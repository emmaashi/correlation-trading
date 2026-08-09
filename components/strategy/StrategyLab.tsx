"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  Loader2,
  Minus,
  Plus,
  Search,
  X,
} from "lucide-react";

import ChartInfoTooltip from "@/components/correlation/ChartInfoTooltip";
import Toast from "@/components/correlation/Toast";
import { todayISO, yearsAgoISO } from "@/lib/dateUtils";
import type {
  BasketSignal,
  ModelQuality,
  StrategyAction,
  StrategyBacktestResponse,
  StrategyScanResponse,
  StrategyUniversesResponse,
} from "@/lib/strategyTypes";
import {
  StrategyDrawdownChart,
  StrategyEquityChart,
  StrategyResidualChart,
} from "./StrategyCharts";

const DEFAULT_START = yearsAgoISO(5);
const DEFAULT_END = todayISO();
const TICKER_PATTERN = /^[A-Z0-9.-]{1,10}$/;

function formatPercent(value: number | null | undefined, digits = 1) {
  return value == null ? "--" : `${(value * 100).toFixed(digits)}%`;
}

function formatMoney(value: number | null | undefined) {
  return value == null
    ? "--"
    : value.toLocaleString(undefined, {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      });
}

function formatNumber(value: number | null | undefined, digits = 2) {
  return value == null ? "--" : value.toFixed(digits);
}

function actionPresentation(action: StrategyAction, target: string) {
  if (action === "long_target") {
    return {
      label: `Long ${target}`,
      secondary: "Short peer basket",
      color: "text-emerald-400",
      dot: "bg-emerald-400",
      icon: ArrowUpRight,
    };
  }
  if (action === "short_target") {
    return {
      label: `Short ${target}`,
      secondary: "Long peer basket",
      color: "text-red-400",
      dot: "bg-red-400",
      icon: ArrowDownRight,
    };
  }
  return {
    label: action === "hold" ? "Hold" : "Unavailable",
    secondary:
      action === "hold" ? "Residual is inside the entry bands" : "Signal could not be estimated",
    color: "text-neutral-300",
    dot: "bg-neutral-500",
    icon: Minus,
  };
}

const qualityStyles: Record<ModelQuality, string> = {
  strong: "border-emerald-500/25 bg-emerald-500/10 text-emerald-400",
  moderate: "border-amber-500/25 bg-amber-500/10 text-amber-300",
  weak: "border-red-500/25 bg-red-500/10 text-red-400",
};

async function responseJson<T>(response: Response): Promise<T> {
  let payload: any;
  try {
    payload = await response.json();
  } catch {
    throw new Error(
      response.status >= 500
        ? "Strategy API is unavailable. Please try again."
        : "Strategy API returned an invalid response. Please try again."
    );
  }
  if (!response.ok) {
    throw new Error(payload.error?.message ?? payload.error ?? "Request failed");
  }
  return payload as T;
}

function Metric({ label, value, help }: { label: string; value: string; help: string }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-1">
        <span className="text-[10px] font-medium uppercase text-neutral-500">{label}</span>
        <ChartInfoTooltip label={label}>{help}</ChartInfoTooltip>
      </div>
      <p className="mt-1 truncate font-mono text-lg font-semibold text-neutral-100">{value}</p>
    </div>
  );
}

export default function StrategyLab() {
  const [universes, setUniverses] = useState<StrategyUniversesResponse | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [tickers, setTickers] = useState<string[]>([]);
  const [tickerInput, setTickerInput] = useState("");
  const [validatingTicker, setValidatingTicker] = useState(false);
  const [tickerToast, setTickerToast] = useState<string | null>(null);
  const [loadingUniverses, setLoadingUniverses] = useState(false);
  const [dateRange, setDateRange] = useState({ start: DEFAULT_START, end: DEFAULT_END });
  const [scanning, setScanning] = useState(false);
  const [scan, setScan] = useState<StrategyScanResponse | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<BasketSignal | null>(null);
  const [backtest, setBacktest] = useState<StrategyBacktestResponse | null>(null);
  const [backtesting, setBacktesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialScanStarted, setInitialScanStarted] = useState(false);
  const detailRef = useRef<HTMLDivElement | null>(null);

  const loadUniverses = useCallback(async (signal?: AbortSignal) => {
    setLoadingUniverses(true);
    setError(null);
    try {
      const response = await fetch("/api/strategy/universes", { signal });
      const payload = await responseJson<StrategyUniversesResponse>(response);
      const first = payload.groups[0];
      if (!first) throw new Error("No peer groups are available.");

      setUniverses(payload);
      setSelectedGroupId(first.id);
      setTickers(first.members.map((member) => member.ticker));
    } catch (requestError: any) {
      if (!signal?.aborted) {
        setError(requestError.message ?? "Could not load peer groups");
      }
    } finally {
      if (!signal?.aborted) setLoadingUniverses(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadUniverses(controller.signal);
    return () => controller.abort();
  }, [loadUniverses]);

  const runScan = useCallback(
    async (symbols = tickers) => {
      if (symbols.length < 4 || symbols.length > 8) return;
      setScanning(true);
      setError(null);
      setSelectedCandidate(null);
      setBacktest(null);
      try {
        const response = await fetch("/api/strategy/scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tickers: symbols,
            start: dateRange.start,
            end: dateRange.end,
          }),
        });
        setScan(await responseJson<StrategyScanResponse>(response));
      } catch (requestError: any) {
        setError(requestError.message ?? "Could not scan the peer group");
      } finally {
        setScanning(false);
      }
    },
    [dateRange, tickers]
  );

  useEffect(() => {
    if (!universes || initialScanStarted || tickers.length < 4) return;
    setInitialScanStarted(true);
    void runScan(tickers);
  }, [initialScanStarted, runScan, tickers, universes]);

  const selectedGroup = useMemo(
    () => universes?.groups.find((group) => group.id === selectedGroupId) ?? null,
    [selectedGroupId, universes]
  );

  const selectGroup = (groupId: string) => {
    const group = universes?.groups.find((candidate) => candidate.id === groupId);
    if (!group) return;
    setSelectedGroupId(groupId);
    setTickers(group.members.map((member) => member.ticker));
    setScan(null);
    setBacktest(null);
    setSelectedCandidate(null);
  };

  const addTicker = async (event?: FormEvent) => {
    event?.preventDefault();
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker || tickers.includes(ticker) || tickers.length >= 8 || validatingTicker) return;
    if (!TICKER_PATTERN.test(ticker)) {
      setTickerToast(`"${ticker}" is not a valid ticker symbol`);
      return;
    }

    setValidatingTicker(true);
    setTickerToast(null);
    try {
      const response = await fetch(`/api/validate?ticker=${encodeURIComponent(ticker)}`);
      const payload = await responseJson<{ valid: boolean; error?: string }>(response);
      if (!payload.valid) {
        setTickerToast(payload.error ?? `"${ticker}" is not a valid ticker symbol`);
        return;
      }

      setTickers((current) => [...current, ticker]);
      setTickerInput("");
      setScan(null);
      setSelectedCandidate(null);
      setBacktest(null);
    } catch {
      setTickerToast(`Could not validate "${ticker}". Please try again.`);
    } finally {
      setValidatingTicker(false);
    }
  };

  const runBacktest = async (candidate: BasketSignal) => {
    setSelectedCandidate(candidate);
    setBacktest(null);
    setBacktesting(true);
    setError(null);
    requestAnimationFrame(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    try {
      const response = await fetch("/api/strategy/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: candidate.target,
          peers: candidate.peers,
          start: dateRange.start,
          end: dateRange.end,
          initial_capital: 100000,
          gross_exposure: 1,
          transaction_cost_bps: 5,
          annual_borrow_rate: 0.03,
          participation_rate: 0.01,
        }),
      });
      setBacktest(await responseJson<StrategyBacktestResponse>(response));
    } catch (requestError: any) {
      setError(requestError.message ?? "Could not run the strategy backtest");
    } finally {
      setBacktesting(false);
    }
  };

  return (
    <div className="pt-8 sm:pt-10">
      {tickerToast && (
        <Toast
          key={tickerToast}
          message={tickerToast}
          type="error"
          duration={8000}
          onClose={() => setTickerToast(null)}
        />
      )}
      <header className="mx-auto max-w-2xl text-center">
        <h1 className="text-3xl font-bold text-neutral-50 sm:text-4xl">Strategy Lab</h1>
        <p className="mt-2 text-sm leading-6 text-neutral-400 sm:text-base">
          Scan a related peer group, inspect relative-value signals, and test the exact long-short rule out of sample.
        </p>
      </header>

      <section className="mt-8 border-y border-white/[0.08] py-5">
        <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)_auto] lg:items-end">
          <label className="block">
            <span className="mb-1.5 block text-[10px] font-medium uppercase text-neutral-500">Peer group</span>
            <div className="relative">
              <select
                value={selectedGroupId}
                onChange={(event) => selectGroup(event.target.value)}
                className="h-9 w-full appearance-none rounded-md border border-white/[0.10] bg-neutral-950 px-3 pr-8 text-sm text-neutral-200 outline-none transition-colors focus:border-[#c28b00]/60"
              >
                {universes?.groups.map((group) => (
                  <option key={group.id} value={group.id}>{group.name}</option>
                ))}
              </select>
              <ChevronDown aria-hidden="true" className="pointer-events-none absolute right-2.5 top-2.5 h-4 w-4 text-neutral-600" />
            </div>
          </label>

          <div>
            <span className="mb-1.5 block text-[10px] font-medium uppercase text-neutral-500">Editable universe</span>
            <div className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-white/[0.10] bg-neutral-950 px-2 py-1.5 focus-within:border-[#c28b00]/60">
              {tickers.map((ticker) => (
                <span key={ticker} className="inline-flex h-6 items-center gap-1 rounded bg-white/[0.08] pl-2 pr-1 font-mono text-xs text-neutral-200">
                  {ticker}
                  <button
                    type="button"
                    aria-label={`Remove ${ticker}`}
                    onClick={() => {
                      setTickers((current) => current.filter((item) => item !== ticker));
                      setScan(null);
                      setSelectedCandidate(null);
                      setBacktest(null);
                    }}
                    className="inline-flex h-5 w-5 items-center justify-center text-neutral-500 hover:text-neutral-100"
                  >
                    <X aria-hidden="true" className="h-3 w-3" />
                  </button>
                </span>
              ))}
              {tickers.length < 8 && (
                <form onSubmit={addTicker} className="flex min-w-[90px] flex-1 items-center">
                  <button
                    type="submit"
                    aria-label="Add ticker"
                    title="Add ticker"
                    disabled={validatingTicker || !tickerInput.trim()}
                    className="inline-flex h-6 w-6 shrink-0 items-center justify-center text-neutral-600 transition-colors hover:text-neutral-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {validatingTicker ? (
                      <Loader2 aria-hidden="true" className="h-3.5 w-3.5 animate-spin text-[#d4a020]" />
                    ) : (
                      <Plus aria-hidden="true" className="h-3.5 w-3.5" />
                    )}
                  </button>
                  <input
                    aria-label="Add ticker"
                    value={tickerInput}
                    onChange={(event) => setTickerInput(event.target.value.toUpperCase())}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void addTicker();
                      }
                    }}
                    disabled={validatingTicker}
                    aria-busy={validatingTicker}
                    placeholder={validatingTicker ? "Checking" : "Add ticker"}
                    className="min-w-0 flex-1 bg-transparent px-1.5 font-mono text-xs text-neutral-100 placeholder:text-neutral-700 focus:outline-none"
                  />
                </form>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={() => void runScan()}
            disabled={scanning || tickers.length < 4 || tickers.length > 8 || dateRange.start >= dateRange.end}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-[#c28b00] px-4 text-sm font-semibold text-black transition-colors hover:bg-[#d4a020] disabled:cursor-not-allowed disabled:opacity-35"
          >
            {scanning ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <Search aria-hidden="true" className="h-4 w-4" />}
            {scanning ? "Scanning" : "Scan signals"}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label>
            <span className="mb-1 block text-[10px] uppercase text-neutral-600">Start</span>
            <input type="date" value={dateRange.start} onChange={(event) => setDateRange((current) => ({ ...current, start: event.target.value }))} className="h-8 rounded-md border border-white/[0.08] bg-neutral-950 px-2 text-xs text-neutral-400 outline-none focus:border-[#c28b00]/50" />
          </label>
          <label>
            <span className="mb-1 block text-[10px] uppercase text-neutral-600">End</span>
            <input type="date" value={dateRange.end} onChange={(event) => setDateRange((current) => ({ ...current, end: event.target.value }))} className="h-8 rounded-md border border-white/[0.08] bg-neutral-950 px-2 text-xs text-neutral-400 outline-none focus:border-[#c28b00]/50" />
          </label>
          <p className="max-w-xl pb-1 text-[11px] leading-4 text-neutral-600">
            Scanner ranking uses a fixed 252-session model. Detailed results compare 126, 252, and 504-session formation windows without choosing the winner.
          </p>
        </div>
      </section>

      {error && (
        <div className="mt-5 flex items-center gap-3 rounded-md border border-red-500/20 bg-red-500/[0.06] px-4 py-3 text-sm text-red-300">
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span className="min-w-0 flex-1">{error}</span>
          {!universes && (
            <button
              type="button"
              onClick={() => void loadUniverses()}
              disabled={loadingUniverses}
              className="inline-flex h-7 shrink-0 items-center gap-1.5 rounded border border-red-400/25 px-2.5 text-xs font-medium text-red-200 transition-colors hover:bg-red-400/10 disabled:cursor-wait disabled:opacity-60"
            >
              {loadingUniverses && <Loader2 aria-hidden="true" className="h-3.5 w-3.5 animate-spin" />}
              {loadingUniverses ? "Retrying" : "Retry"}
            </button>
          )}
        </div>
      )}

      <section className="mt-6 overflow-hidden rounded-lg border border-white/[0.09]">
        <div className="flex flex-col gap-2 border-b border-white/[0.08] bg-white/[0.025] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-1.5">
            <h2 className="text-sm font-semibold text-neutral-100">Opportunity Scanner</h2>
            <ChartInfoTooltip label="Opportunity Scanner">
              Each stock is compared with a weighted basket of the other selected companies. Larger absolute residual z-scores indicate a more unusual relative move, while model quality shows how much historical evidence supports mean reversion.
            </ChartInfoTooltip>
          </div>
          <p className="text-[11px] text-neutral-500">
            {scan ? `${selectedGroup?.name ?? "Custom group"} · data through ${scan.as_of}` : "Choose 4–8 related stocks"}
          </p>
        </div>

        {scanning && !scan ? (
          <div className="flex h-52 items-center justify-center gap-2 text-sm text-neutral-500">
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            Fitting each peer basket
          </div>
        ) : scan?.candidates.length ? (
          <div className="divide-y divide-white/[0.07]">
            {scan.candidates.map((candidate, index) => {
              const presentation = actionPresentation(candidate.action, candidate.target);
              const Icon = presentation.icon;
              return (
                <button
                  type="button"
                  key={candidate.target}
                  onClick={() => void runBacktest(candidate)}
                  className={`grid w-full grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.035] sm:grid-cols-[34px_100px_minmax(180px,1fr)_100px_120px_24px] ${selectedCandidate?.target === candidate.target ? "bg-white/[0.045]" : ""}`}
                >
                  <span className="font-mono text-xs text-neutral-600">{String(index + 1).padStart(2, "0")}</span>
                  <span className="min-w-0">
                    <span className="block font-mono text-sm font-semibold text-neutral-100">{candidate.target}</span>
                    <span className={`mt-0.5 block truncate text-[10px] sm:hidden ${presentation.color}`}>
                      {presentation.label}
                    </span>
                  </span>
                  <span className="hidden min-w-0 sm:block">
                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${presentation.color}`}>
                      <Icon aria-hidden="true" className="h-3.5 w-3.5" />
                      {presentation.label}
                    </span>
                    <span className="ml-2 text-[11px] text-neutral-600">{presentation.secondary}</span>
                  </span>
                  <span className="text-right font-mono text-sm text-neutral-200">{formatNumber(candidate.zscore)}</span>
                  <span className={`hidden justify-self-end rounded border px-2 py-0.5 text-[10px] font-medium capitalize sm:inline-flex ${qualityStyles[candidate.model_quality]}`}>
                    {candidate.model_quality}
                  </span>
                  <ArrowRight aria-hidden="true" className="h-4 w-4 text-neutral-600" />
                </button>
              );
            })}
          </div>
        ) : (
          <div className="flex h-52 items-center justify-center text-sm text-neutral-600">No scan has been run yet.</div>
        )}
      </section>

      <div ref={detailRef} className="scroll-mt-6">
        {selectedCandidate && backtesting && (
          <div className="mt-10 flex h-64 items-center justify-center gap-2 border-y border-white/[0.08] text-sm text-neutral-500">
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            Running three walk-forward simulations for {selectedCandidate.target}
          </div>
        )}

        {backtest && <BacktestDetail result={backtest} />}
      </div>

      <div className="mt-8 flex items-start gap-2 border-t border-white/[0.08] pt-4 text-[11px] leading-5 text-neutral-600">
        <AlertTriangle aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
        <p>
          Research simulation only. Signals are estimates from Yahoo Finance data and current editable peer sets. They are not investment advice, risk-free arbitrage, or a guarantee of future performance.
        </p>
      </div>
    </div>
  );
}

function BacktestDetail({ result }: { result: StrategyBacktestResponse }) {
  const signal = result.current_signal;
  const presentation = actionPresentation(signal.action, result.target);
  const ActionIcon = presentation.icon;

  return (
    <div className="mt-10 space-y-6">
      <section className="rounded-lg border border-white/[0.10] bg-white/[0.025]">
        <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.75fr)]">
          <div>
            <p className="text-[10px] font-medium uppercase text-neutral-500">Current research signal · {result.as_of}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <span className={`inline-flex items-center gap-2 text-xl font-semibold ${presentation.color}`}>
                <ActionIcon aria-hidden="true" className="h-5 w-5" />
                {presentation.label}
              </span>
              <span className="text-sm text-neutral-500">{presentation.secondary}</span>
            </div>
            <p className="mt-3 max-w-2xl text-xs leading-5 text-neutral-500">
              {signal.action === "hold"
                ? `${result.target} is not far enough from its fitted peer basket to cross the predeclared entry threshold.`
                : `The model treats ${result.target}'s residual as historically unusual. The hedge basket is required; this is not a standalone directional forecast.`}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-2">
            <Metric label="Residual z" value={formatNumber(signal.zscore)} help="Distance between the current residual and its estimated equilibrium, measured in standard deviations. The fixed entry threshold is ±2." />
            <Metric label="Model quality" value={signal.model_quality} help="Advisory summary of stationarity, half-life, explanatory power, and basket concentration. It is evidence quality, not a probability of profit." />
            <Metric label="Half-life" value={signal.half_life_days == null ? "--" : `${signal.half_life_days.toFixed(1)}d`} help="Estimated time for half of a residual deviation to decay. Shorter is faster; instability can make this estimate unreliable." />
            <Metric label="Explained" value={formatPercent(signal.r_squared)} help="Share of target return variance explained by the fitted peers during the formation window. A high value alone does not prove mean reversion." />
          </div>
        </div>
        <div className="border-t border-white/[0.08] px-5 py-4">
          <div className="mb-3 flex items-center gap-1.5">
            <h3 className="text-xs font-semibold text-neutral-200">Tradeable peer hedge</h3>
            <ChartInfoTooltip label="Tradeable peer hedge">
              These are the peer-basket weights used on the opposite side of the target. Hedge beta sets the total basket notional, then each weight divides that notional among peers.
            </ChartInfoTooltip>
            <span className="ml-auto font-mono text-[11px] text-neutral-500">beta {formatNumber(signal.hedge_beta)}</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {signal.peer_weights.map((peer) => (
              <div key={peer.ticker}>
                <div className="flex justify-between font-mono text-[11px] text-neutral-400">
                  <span>{peer.ticker}</span>
                  <span>{formatPercent(peer.weight, 0)}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/[0.07]">
                  <div className="h-full rounded-full bg-[#c28b00]" style={{ width: `${Math.max(2, peer.weight * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 rounded-lg border border-white/[0.09] px-4 py-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <Metric label="Net return" value={formatPercent(result.summary.total_return)} help="Change in simulated equity after transaction and borrow costs." />
        <Metric label="Recent holdout" value={formatPercent(result.summary.holdout.total_return)} help="Net return from the final 30% of the walk-forward period, reported separately to expose recent degradation." />
        <Metric label="Sharpe" value={formatNumber(result.summary.sharpe)} help="Annualized average daily return divided by daily volatility, using a zero risk-free rate." />
        <Metric label="Max drawdown" value={formatPercent(result.summary.max_drawdown)} help="Worst peak-to-trough loss in simulated strategy equity." />
        <Metric label="Trades" value={String(result.summary.trade_count)} help="Completed long-target or short-target round trips." />
        <Metric label="Win rate" value={formatPercent(result.summary.win_rate)} help="Share of completed trades with positive net P&L. It does not show the size of wins versus losses." />
        <Metric label="Turnover" value={`${formatNumber(result.summary.turnover)}x`} help="Total traded notional divided by starting capital. High turnover makes results more sensitive to execution costs." />
        <Metric label="Costs" value={formatMoney(result.costs.total)} help="Simulated slippage plus annualized short-borrow charges deducted from cash." />
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <StrategyEquityChart data={result.equity_curve} />
        <StrategyResidualChart data={result.residual_series} />
      </div>
      <StrategyDrawdownChart data={result.equity_curve} />

      <section className="rounded-lg border border-white/[0.09]">
        <div className="flex items-center gap-1.5 border-b border-white/[0.08] px-4 py-3">
          <h3 className="text-sm font-semibold text-neutral-100">Predeclared Sensitivity</h3>
          <ChartInfoTooltip label="Predeclared Sensitivity">
            The same rules are tested with short, base, and long formation windows. The application reports every result and never promotes whichever window happened to perform best.
          </ChartInfoTooltip>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-xs">
            <thead className="border-b border-white/[0.07] text-[10px] uppercase text-neutral-600">
              <tr><th className="px-4 py-2 font-medium">Formation</th><th className="px-4 py-2 font-medium">Net return</th><th className="px-4 py-2 font-medium">Recent holdout</th><th className="px-4 py-2 font-medium">Sharpe</th><th className="px-4 py-2 font-medium">Drawdown</th><th className="px-4 py-2 font-medium">Trades</th></tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              {result.sensitivity.map((entry) => (
                <tr key={entry.formation_window} className="text-neutral-300">
                  <td className="px-4 py-3 font-mono">{entry.formation_window} sessions{entry.formation_window === 252 ? <span className="ml-2 text-[10px] text-[#d4a020]">base</span> : null}</td>
                  {entry.status === "available" && entry.summary ? (
                    <><td className="px-4 py-3 font-mono">{formatPercent(entry.summary.total_return)}</td><td className="px-4 py-3 font-mono">{formatPercent(entry.summary.holdout.total_return)}</td><td className="px-4 py-3 font-mono">{formatNumber(entry.summary.sharpe)}</td><td className="px-4 py-3 font-mono">{formatPercent(entry.summary.max_drawdown)}</td><td className="px-4 py-3 font-mono">{entry.summary.trade_count}</td></>
                  ) : <td className="px-4 py-3 text-neutral-600" colSpan={5}>{entry.error ?? "Unavailable"}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-white/[0.09]">
        <div className="flex items-center justify-between border-b border-white/[0.08] px-4 py-3">
          <h3 className="text-sm font-semibold text-neutral-100">Trade Ledger</h3>
          <span className="text-[11px] text-neutral-600">{result.trades.length} completed trades</span>
        </div>
        <div className="max-h-[360px] overflow-auto">
          <table className="w-full min-w-[820px] text-left text-xs">
            <thead className="sticky top-0 bg-neutral-950 text-[10px] uppercase text-neutral-600">
              <tr><th className="px-4 py-2 font-medium">Signal</th><th className="px-4 py-2 font-medium">Entry</th><th className="px-4 py-2 font-medium">Exit</th><th className="px-4 py-2 font-medium">Side</th><th className="px-4 py-2 font-medium">Entry z</th><th className="px-4 py-2 font-medium">Held</th><th className="px-4 py-2 font-medium">Exit reason</th><th className="px-4 py-2 text-right font-medium">Net P&L</th></tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              {result.trades.map((trade, index) => (
                <tr key={`${trade.entry_date}-${index}`} className="text-neutral-400">
                  <td className="px-4 py-2.5 font-mono">{trade.signal_date}</td><td className="px-4 py-2.5 font-mono">{trade.entry_date}</td><td className="px-4 py-2.5 font-mono">{trade.exit_date}</td><td className={`px-4 py-2.5 font-medium ${trade.direction === "long_target" ? "text-emerald-400" : "text-red-400"}`}>{trade.direction === "long_target" ? `Long ${result.target}` : `Short ${result.target}`}</td><td className="px-4 py-2.5 font-mono">{formatNumber(trade.entry_zscore)}</td><td className="px-4 py-2.5 font-mono">{trade.holding_sessions}d</td><td className="px-4 py-2.5">{trade.exit_reason.replaceAll("_", " ")}</td><td className={`px-4 py-2.5 text-right font-mono ${(trade.net_pnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>{formatMoney(trade.net_pnl)}</td>
                </tr>
              ))}
              {!result.trades.length && <tr><td colSpan={8} className="px-4 py-8 text-center text-neutral-600">No entry threshold was crossed in this period.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <details className="group rounded-lg border border-white/[0.09]">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-neutral-300">
          {signal.cautions.length ? <AlertTriangle aria-hidden="true" className="h-4 w-4 text-amber-400" /> : <CheckCircle2 aria-hidden="true" className="h-4 w-4 text-emerald-400" />}
          Model and data cautions
          <ChevronDown aria-hidden="true" className="ml-auto h-4 w-4 text-neutral-600 transition-transform group-open:rotate-180" />
        </summary>
        <div className="border-t border-white/[0.08] px-4 py-4 text-xs leading-5 text-neutral-500">
          <ul className="space-y-1.5">
            {[...signal.cautions, ...result.data_quality.warnings, ...result.capacity_warnings].map((warning) => <li key={warning}>• {warning}</li>)}
          </ul>
          <p className="mt-3 border-t border-white/[0.07] pt-3">{result.methodology_note}</p>
        </div>
      </details>
    </div>
  );
}
