"use client";

import { SignalLevel, getSignalColor } from "@/lib/correlationTypes";

interface SignalBadgeProps {
  level: SignalLevel;
  label?: string;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}

export default function SignalBadge({
  level,
  label,
  size = "md",
  pulse = true,
}: SignalBadgeProps) {
  const color = getSignalColor(level);
  const displayLabel =
    label ?? (level === "signal" ? "Signal" : level === "watch" ? "Watch" : "Normal");

  const dotSize = size === "sm" ? "h-2 w-2" : size === "lg" ? "h-3.5 w-3.5" : "h-2.5 w-2.5";
  const textSize = size === "sm" ? "text-[10px]" : size === "lg" ? "text-sm" : "text-xs";

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex">
        {pulse && level === "signal" && (
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-50"
            style={{ backgroundColor: color }}
          />
        )}
        <span
          className={`relative inline-flex rounded-full ${dotSize}`}
          style={{ backgroundColor: color }}
        />
      </span>
      <span className={`${textSize} font-medium`} style={{ color }}>
        {displayLabel}
      </span>
    </span>
  );
}
