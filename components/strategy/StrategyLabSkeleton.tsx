function SkeletonBlock({ className }: { className: string }) {
  return <div className={`rounded bg-white/[0.065] ${className}`} />;
}

export default function StrategyLabSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading Strategy Lab"
      aria-busy="true"
      className="pointer-events-none pt-8 motion-safe:animate-pulse sm:pt-10"
    >
      <span className="sr-only">Loading Strategy Lab</span>

      <header className="mx-auto flex max-w-2xl flex-col items-center">
        <SkeletonBlock className="h-10 w-52 sm:w-64" />
        <SkeletonBlock className="mt-4 h-4 w-full max-w-xl" />
        <SkeletonBlock className="mt-2 h-4 w-72 max-w-[80%]" />
      </header>

      <section className="mt-8 border-y border-white/[0.08] py-5">
        <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)_auto] lg:items-end">
          <div>
            <SkeletonBlock className="mb-2 h-2.5 w-16" />
            <SkeletonBlock className="h-9 w-full" />
          </div>
          <div>
            <SkeletonBlock className="mb-2 h-2.5 w-24" />
            <SkeletonBlock className="h-9 w-full" />
          </div>
          <SkeletonBlock className="h-9 w-full lg:w-32" />
        </div>

        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <SkeletonBlock className="mb-2 h-2.5 w-10" />
            <SkeletonBlock className="h-9 w-[154px]" />
          </div>
          <div>
            <SkeletonBlock className="mb-2 h-2.5 w-8" />
            <SkeletonBlock className="h-9 w-[154px]" />
          </div>
          <div className="pb-1">
            <SkeletonBlock className="h-3 w-80 max-w-[55vw]" />
            <SkeletonBlock className="mt-2 h-3 w-56 max-w-[42vw]" />
          </div>
        </div>
      </section>

      <section className="mt-6 overflow-hidden rounded-lg border border-white/[0.09]">
        <div className="flex items-center justify-between border-b border-white/[0.08] bg-white/[0.025] px-4 py-3">
          <SkeletonBlock className="h-4 w-36" />
          <SkeletonBlock className="h-3 w-52 max-w-[36vw]" />
        </div>
        <div className="divide-y divide-white/[0.07]">
          {[0, 1, 2, 3].map((row) => (
            <div
              key={row}
              className="grid grid-cols-[28px_minmax(0,1fr)_72px] items-center gap-3 px-4 py-4 sm:grid-cols-[34px_100px_minmax(180px,1fr)_100px_120px_24px]"
            >
              <SkeletonBlock className="h-3 w-5" />
              <SkeletonBlock className="h-4 w-14" />
              <SkeletonBlock className="hidden h-3 w-52 sm:block" />
              <SkeletonBlock className="h-4 w-12 justify-self-end" />
              <SkeletonBlock className="hidden h-6 w-16 justify-self-end sm:block" />
              <SkeletonBlock className="hidden h-4 w-4 sm:block" />
            </div>
          ))}
        </div>
      </section>

      <div className="mt-8 border-t border-white/[0.08] pt-4">
        <SkeletonBlock className="h-3 w-full max-w-4xl" />
      </div>
    </div>
  );
}
