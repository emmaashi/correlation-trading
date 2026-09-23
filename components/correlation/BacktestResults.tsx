"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { BacktestResponse } from "@/lib/correlationTypes";

interface BacktestResultsProps {
  data: BacktestResponse;
}

export default function BacktestResults({ data }: BacktestResultsProps) {
  const { metrics, equity_curve, trade_log } = data;

  return (
    <div className="mt-6 space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
          <p className="text-neutral-400 text-xs uppercase tracking-wide">Total Return</p>
          <p className={`text-xl font-medium mt-1 ${equity_curve.length > 0 && equity_curve[equity_curve.length - 1].value >= 0 ? "text-green-400" : "text-red-400"}`}>
            {equity_curve.length > 0
              ? (equity_curve[equity_curve.length - 1].value * 100).toFixed(2)
              : "0.00"}%
          </p>
        </div>
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
          <p className="text-neutral-400 text-xs uppercase tracking-wide">Sharpe Ratio</p>
          <p className="text-xl text-neutral-50 font-medium mt-1">
            {metrics.sharpe.toFixed(2)}
          </p>
        </div>
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
          <p className="text-neutral-400 text-xs uppercase tracking-wide">Max Drawdown</p>
          <p className="text-xl text-red-400 font-medium mt-1">
            {(metrics.max_drawdown * 100).toFixed(2)}%
          </p>
        </div>
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
          <p className="text-neutral-400 text-xs uppercase tracking-wide">Win Rate / Trades</p>
          <p className="text-xl text-neutral-50 font-medium mt-1">
            {(metrics.win_rate * 100).toFixed(1)}% <span className="text-sm text-neutral-500 font-normal">({metrics.num_trades})</span>
          </p>
        </div>
      </div>

      {/* Equity Curve Chart */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-neutral-300 mb-1">
          Equity Curve
        </h3>
        <p className="text-xs text-neutral-500 mb-4">
          Cumulative return of the walk-forward backtest
        </p>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={equity_curve} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#737373", fontSize: 11 }}
                axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                tickLine={false}
                minTickGap={30}
              />
              <YAxis
                tick={{ fill: "#737373", fontSize: 11 }}
                axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                tickLine={false}
                tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(0,0,0,0.85)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "12px",
                  backdropFilter: "blur(12px)",
                  fontSize: 12,
                  color: "#e5e5e5",
                }}
                formatter={(value: number) => [`${(value * 100).toFixed(2)}%`, "Return"]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#c28b00"
                strokeWidth={2}
                dot={false}
                activeDot={{
                  r: 6,
                  stroke: "#c28b00",
                  strokeWidth: 2,
                  fill: "#000",
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Trade Log */}
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-neutral-300 mb-4">
          Trade Log
        </h3>
        {trade_log.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-neutral-300">
              <thead className="text-xs text-neutral-500 uppercase bg-white/[0.03]">
                <tr>
                  <th className="px-4 py-2 rounded-tl-lg">Type</th>
                  <th className="px-4 py-2">Entry Date</th>
                  <th className="px-4 py-2">Exit Date</th>
                  <th className="px-4 py-2">Days</th>
                  <th className="px-4 py-2">Entry Z/Spread</th>
                  <th className="px-4 py-2">Exit Z/Spread</th>
                  <th className="px-4 py-2 text-right rounded-tr-lg">P&L</th>
                </tr>
              </thead>
              <tbody>
                {trade_log.map((trade, idx) => (
                  <tr key={idx} className="border-b border-white/[0.02] last:border-0 hover:bg-white/[0.01]">
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${trade.type === "LONG" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
                        {trade.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-neutral-400">{trade.entry_date}</td>
                    <td className="px-4 py-3 font-mono text-xs text-neutral-400">{trade.exit_date}</td>
                    <td className="px-4 py-3 text-xs">{trade.holding_period}</td>
                    <td className="px-4 py-3 font-mono text-xs text-neutral-400">
                      {trade.entry_spread.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-neutral-400">
                      {trade.exit_spread.toFixed(4)}
                    </td>
                    <td className={`px-4 py-3 text-right font-medium ${trade.pnl_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {(trade.pnl_pct * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-neutral-500 text-center py-6">
            No trades were executed with these parameters.
          </p>
        )}
      </div>
    </div>
  );
}
