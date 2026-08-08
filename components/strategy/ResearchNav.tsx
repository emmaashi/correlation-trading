"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Network } from "lucide-react";

const links = [
  { href: "/", label: "Pair Explorer", icon: Network },
  { href: "/strategy-lab", label: "Strategy Lab", icon: BarChart3 },
];

export default function ResearchNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Research tools" className="flex justify-center">
      <div className="inline-flex h-9 items-center rounded-lg border border-white/[0.09] bg-white/[0.035] p-1">
        {links.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`inline-flex h-7 items-center gap-2 rounded-md px-3 text-xs font-medium transition-colors sm:px-4 ${
                active
                  ? "bg-white/[0.11] text-neutral-100"
                  : "text-neutral-500 hover:text-neutral-200"
              }`}
            >
              <Icon aria-hidden="true" className="h-3.5 w-3.5" />
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
