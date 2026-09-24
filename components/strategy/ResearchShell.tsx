"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";
import type { ReactNode } from "react";

import PairExplorerSkeleton from "@/components/correlation/PairExplorerSkeleton";
import ResearchNav from "./ResearchNav";
import StrategyLabSkeleton from "./StrategyLabSkeleton";

const MINIMUM_SKELETON_MS = 500;

type TransitionTarget = "pair" | "strategy";

function targetFromHref(href: string): TransitionTarget {
  return href === "/" ? "pair" : "strategy";
}

function routeMatches(target: TransitionTarget, pathname: string) {
  return target === "pair" ? pathname === "/" : pathname.startsWith("/strategy-lab");
}

export default function ResearchShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const reduceMotion = useReducedMotion();
  const fallbackTimer = useRef<number | null>(null);

  const clearTransition = useCallback(() => {
    delete document.documentElement.dataset.researchTransition;
    delete document.documentElement.dataset.researchTransitionStarted;
    if (fallbackTimer.current !== null) {
      window.clearTimeout(fallbackTimer.current);
      fallbackTimer.current = null;
    }
  }, []);

  const beginTransition = useCallback(
    (href: string) => {
      const target = targetFromHref(href);
      if (routeMatches(target, pathname)) return;

      document.documentElement.dataset.researchTransition = target;
      document.documentElement.dataset.researchTransitionStarted = String(Date.now());
      if (fallbackTimer.current !== null) window.clearTimeout(fallbackTimer.current);
      fallbackTimer.current = window.setTimeout(clearTransition, 10000);
    },
    [clearTransition, pathname]
  );

  useEffect(() => {
    const target = document.documentElement.dataset
      .researchTransition as TransitionTarget | undefined;
    if (!target || !routeMatches(target, pathname)) return;

    const startedAt = Number(
      document.documentElement.dataset.researchTransitionStarted ?? Date.now()
    );
    const elapsed = Date.now() - startedAt;
    const timer = window.setTimeout(
      clearTransition,
      Math.max(0, MINIMUM_SKELETON_MS - elapsed)
    );
    return () => window.clearTimeout(timer);
  }, [clearTransition, pathname]);

  return (
    <div className="min-h-screen overflow-x-hidden bg-black text-neutral-50">
      <div className="relative z-20 pt-8">
        <ResearchNav onNavigateStart={beginTransition} />
      </div>
      <div className="research-route-skeletons">
        <div className="research-route-skeleton-pair">
          <PairExplorerSkeleton />
        </div>
        <div className="research-route-skeleton-strategy">
          <main className="min-h-screen bg-black text-neutral-50">
            <div className="mx-auto min-h-[calc(100vh-68px)] max-w-7xl px-4 pb-8 sm:px-6">
              <StrategyLabSkeleton />
            </div>
          </main>
        </div>
      </div>
      <div className="research-route-content">
        <AnimatePresence initial={false} mode="wait">
          <motion.div
            key={pathname}
            initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -6 }}
            transition={{
              duration: reduceMotion ? 0 : 0.2,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
