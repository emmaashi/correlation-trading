"use client";

import { useId, type ReactNode } from "react";
import { Info } from "lucide-react";

interface ChartInfoTooltipProps {
  label: string;
  children: ReactNode;
}

export default function ChartInfoTooltip({
  label,
  children,
}: ChartInfoTooltipProps) {
  const tooltipId = useId();

  return (
    <span className="group relative inline-flex flex-shrink-0">
      <button
        type="button"
        aria-label={`About ${label}`}
        aria-describedby={tooltipId}
        className="inline-flex h-6 w-6 items-center justify-center rounded-md text-neutral-500 transition-colors hover:bg-white/[0.06] hover:text-neutral-200 focus-visible:bg-white/[0.06] focus-visible:text-neutral-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#c28b00]/60"
      >
        <Info aria-hidden="true" className="h-3.5 w-3.5" />
      </button>
      <span
        id={tooltipId}
        role="tooltip"
        className="pointer-events-none absolute right-0 top-full z-30 mt-2 w-72 max-w-[calc(100vw-3rem)] rounded-lg border border-white/[0.1] bg-neutral-950/95 px-3 py-2.5 text-left text-xs font-normal leading-5 text-neutral-300 opacity-0 shadow-2xl shadow-black/60 backdrop-blur-md transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {children}
      </span>
    </span>
  );
}
