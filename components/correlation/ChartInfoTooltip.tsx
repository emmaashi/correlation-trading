"use client";

import type { ReactNode } from "react";
import * as Popover from "@radix-ui/react-popover";
import { Info, X } from "lucide-react";

interface ChartInfoTooltipProps {
  label: string;
  children: ReactNode;
}

export default function ChartInfoTooltip({
  label,
  children,
}: ChartInfoTooltipProps) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label={`About ${label}`}
          className="inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-md text-neutral-500 transition-colors hover:bg-white/[0.06] hover:text-neutral-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#c28b00]/60 data-[state=open]:bg-[#c28b00]/15 data-[state=open]:text-[#d4a020]"
        >
          <Info aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={8}
          collisionPadding={16}
          aria-label={`${label} explanation`}
          className="z-50 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-white/[0.1] bg-neutral-950/95 p-3 text-left shadow-2xl shadow-black/60 backdrop-blur-md"
        >
          <div className="mb-1.5 flex items-center justify-between gap-3">
            <p className="text-xs font-semibold text-neutral-100">{label}</p>
            <Popover.Close asChild>
              <button
                type="button"
                aria-label={`Close ${label} explanation`}
                className="inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-neutral-500 transition-colors hover:bg-white/[0.06] hover:text-neutral-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#c28b00]/60"
              >
                <X aria-hidden="true" className="h-3.5 w-3.5" />
              </button>
            </Popover.Close>
          </div>
          <p className="text-xs font-normal leading-5 text-neutral-300">
            {children}
          </p>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
