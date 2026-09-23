"use client";

import type { SignalDirection } from "@/lib/correlationTypes";

interface TradingSignalBadgeProps {
  direction: SignalDirection;
  tickerA: string;
  tickerB: string;
}

export default function TradingSignalBadge({
  direction,
  tickerA,
  tickerB,
}: TradingSignalBadgeProps) {
  if (direction === "hold") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[10px] font-medium text-green-400">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        Hold
      </span>
    );
  }

  const shortTicker = direction === "short" ? tickerA : tickerB;
  const longTicker = direction === "short" ? tickerB : tickerA;

  return (
    <span className="flex flex-col items-end gap-0.5 text-[10px] font-medium">
      <span className="inline-flex items-center gap-1 text-red-400">
        <span className="h-2 w-2 rounded-full bg-red-500" />
        Short <span className="font-mono">{shortTicker}</span>
      </span>
      <span className="inline-flex items-center gap-1 text-green-400">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        Long <span className="font-mono">{longTicker}</span>
      </span>
    </span>
  );
}
