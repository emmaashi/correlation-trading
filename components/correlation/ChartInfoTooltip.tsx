"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import * as Popover from "@radix-ui/react-popover";
import { Info } from "lucide-react";

interface ChartInfoTooltipProps {
  label: string;
  children: ReactNode;
}

export default function ChartInfoTooltip({
  label,
  children,
}: ChartInfoTooltipProps) {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelClose = () => {
    if (closeTimer.current !== null) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const showTooltip = () => {
    cancelClose();
    setOpen(true);
  };

  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = setTimeout(() => setOpen(false), 120);
  };

  useEffect(() => cancelClose, []);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Anchor asChild>
        <button
          type="button"
          aria-label={`About ${label}`}
          aria-expanded={open}
          onMouseEnter={showTooltip}
          onMouseLeave={scheduleClose}
          onFocus={showTooltip}
          onBlur={scheduleClose}
          onClick={showTooltip}
          className="inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors hover:bg-white/[0.07] hover:text-neutral-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#c28b00]/70 aria-expanded:bg-white/[0.07] aria-expanded:text-[#d4a020]"
        >
          <Info aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
      </Popover.Anchor>
      <Popover.Portal>
        <Popover.Content
          role="tooltip"
          align="center"
          sideOffset={6}
          collisionPadding={16}
          onMouseEnter={showTooltip}
          onMouseLeave={scheduleClose}
          onOpenAutoFocus={(event) => event.preventDefault()}
          aria-label={`${label} explanation`}
          className="z-50 w-72 max-w-[calc(100vw-2rem)] rounded-md border border-white/[0.12] bg-neutral-950 p-3 text-left shadow-xl shadow-black/50 outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95"
        >
          <div className="flex items-start gap-2.5">
            <Info
              aria-hidden="true"
              className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-[#d4a020]"
            />
            <div>
              <p className="text-xs font-semibold text-neutral-100">{label}</p>
              <p className="mt-1 text-xs font-normal leading-5 text-neutral-400">
                {children}
              </p>
            </div>
          </div>
          <Popover.Arrow className="fill-neutral-950" width={10} height={5} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
