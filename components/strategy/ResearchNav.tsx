"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { BarChart3, Network } from "lucide-react";

const links = [
  { href: "/", label: "Pair Explorer", icon: Network },
  { href: "/strategy-lab", label: "Strategy Lab", icon: BarChart3 },
];

export default function ResearchNav() {
  const pathname = usePathname();
  const reduceMotion = useReducedMotion();

  return (
    <nav aria-label="Research tools" className="flex justify-center">
      <div className="inline-flex h-9 items-center rounded-lg border border-white/[0.09] bg-neutral-950/90 p-1 shadow-lg shadow-black/20 backdrop-blur-sm">
        {links.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`relative inline-flex h-7 items-center gap-2 rounded-md px-3 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-[#c28b00]/70 sm:px-4 ${active ? "text-neutral-100" : "text-neutral-500 hover:text-neutral-200"}`}
            >
              {active && (
                <motion.span
                  layoutId="research-nav-active"
                  className="absolute inset-0 rounded-md border border-white/[0.04] bg-white/[0.11] shadow-sm shadow-black/30"
                  transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 430, damping: 35 }}
                />
              )}
              <Icon aria-hidden="true" className="relative z-10 h-3.5 w-3.5" />
              <span className="relative z-10">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
