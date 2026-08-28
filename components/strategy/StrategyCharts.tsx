"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import ChartInfoTooltip from "@/components/correlation/ChartInfoTooltip";
import type { EquityPoint, ResidualPoint } from "@/lib/strategyTypes";

const axis = { fill: "#737373", fontSize: 11 };

function dateTick(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    year: "2-digit",
  });
}

function MoneyTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-white/[0.12] bg-neutral-950 px-3 py-2 shadow-xl">
      <p className="text-[11px] text-neutral-500">{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.dataKey} className="mt-1 text-xs" style={{ color: entry.color }}>
          {entry.name}: ${Number(entry.value).toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </p>
      ))}
    </div>
  );
}

function ResidualTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload as ResidualPoint | undefined;
  if (!point) return null;
  return (
    <div className="rounded-md border border-white/[0.12] bg-neutral-950 px-3 py-2 shadow-xl">
      <p className="text-[11px] text-neutral-500">{label}</p>
      <p className="mt-1 font-mono text-xs text-[#d4a020]">
        Residual {point.residual_state?.toFixed(4) ?? "--"}
      </p>
      <p className="mt-1 font-mono text-[11px] text-neutral-400">
        Mean {point.equilibrium_mean?.toFixed(4) ?? "--"}
      </p>
    </div>
  );
}

function DrawdownTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-white/[0.12] bg-neutral-950 px-3 py-2 shadow-xl">
      <p className="text-[11px] text-neutral-500">{label}</p>
      <p className="mt-1 font-mono text-xs text-red-400">
        Drawdown {(Number(payload[0].value) * 100).toFixed(2)}%
      </p>
    </div>
  );
}

export function StrategyEquityChart({ data }: { data: EquityPoint[] }) {
  return (
    <section className="rounded-lg border border-white/[0.09] bg-white/[0.02] p-4 sm:p-5">
      <div className="mb-4 flex items-center gap-1.5">
        <h3 className="text-sm font-semibold text-neutral-100">Walk-Forward Equity</h3>
        <ChartInfoTooltip label="Walk-Forward Equity">
          Simulated strategy value after next-open execution, turnover costs, and short borrow. The target benchmark shows what the same starting capital would have done by simply holding the target stock.
        </ChartInfoTooltip>
      </div>
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 10, bottom: 0, left: 4 }}>
            <CartesianGrid stroke="#171717" strokeDasharray="3 5" vertical={false} />
            <XAxis dataKey="date" tick={axis} tickFormatter={dateTick} minTickGap={52} axisLine={false} tickLine={false} />
            <YAxis tick={axis} tickFormatter={(value) => `$${Math.round(value / 1000)}k`} width={48} axisLine={false} tickLine={false} />
            <Tooltip content={<MoneyTooltip />} />
            <Line type="monotone" dataKey="equity" name="Strategy" stroke="#d4a020" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="benchmark" name="Target" stroke="#60a5fa" strokeWidth={1.5} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function StrategyResidualChart({ data }: { data: ResidualPoint[] }) {
  return (
    <section className="rounded-lg border border-white/[0.09] bg-white/[0.02] p-4 sm:p-5">
      <div className="mb-4 flex items-center gap-1.5">
        <h3 className="text-sm font-semibold text-neutral-100">Current Residual State</h3>
        <ChartInfoTooltip label="Current Residual State">
          The target&apos;s cumulative return left unexplained by its weighted peer hedge. Moving below the lower band supports a long-target signal; moving above the upper band supports a short-target signal. The bands describe history, not a guaranteed reversal.
        </ChartInfoTooltip>
      </div>
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 10, bottom: 0, left: 4 }}>
            <CartesianGrid stroke="#171717" strokeDasharray="3 5" vertical={false} />
            <XAxis dataKey="date" tick={axis} tickFormatter={dateTick} minTickGap={52} axisLine={false} tickLine={false} />
            <YAxis tick={axis} tickFormatter={(value) => Number(value).toFixed(2)} width={48} axisLine={false} tickLine={false} />
            <Tooltip content={<ResidualTooltip />} />
            <Line type="monotone" dataKey="entry_upper" stroke="#ef4444" strokeWidth={1} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="equilibrium_mean" stroke="#737373" strokeWidth={1} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="entry_lower" stroke="#22c55e" strokeWidth={1} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="residual_state" stroke="#d4a020" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function StrategyDrawdownChart({ data }: { data: EquityPoint[] }) {
  return (
    <section className="rounded-lg border border-white/[0.09] bg-white/[0.02] p-4 sm:p-5">
      <div className="mb-4 flex items-center gap-1.5">
        <h3 className="text-sm font-semibold text-neutral-100">Drawdown</h3>
        <ChartInfoTooltip label="Drawdown">
          The percentage decline from the strategy&apos;s previous equity peak. Deeper or longer drawdowns show how much capital and patience the simulated rule would have required.
        </ChartInfoTooltip>
      </div>
      <div className="h-[210px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 10, bottom: 0, left: 4 }}>
            <CartesianGrid stroke="#171717" strokeDasharray="3 5" vertical={false} />
            <XAxis dataKey="date" tick={axis} tickFormatter={dateTick} minTickGap={52} axisLine={false} tickLine={false} />
            <YAxis tick={axis} tickFormatter={(value) => `${(value * 100).toFixed(0)}%`} width={48} axisLine={false} tickLine={false} />
            <Tooltip content={<DrawdownTooltip />} />
            <Area type="monotone" dataKey="drawdown" stroke="#f87171" fill="#ef4444" fillOpacity={0.13} strokeWidth={1.5} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
